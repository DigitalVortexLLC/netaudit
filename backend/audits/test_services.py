"""
Tests for the audit_runner scaffold module and audits.services.run_audit.

Covers:
- Scaffold creation / cleanup (directory structure, file contents)
- Full run_audit lifecycle with mocked HTTP + subprocess
- Status transitions, RuleResult creation, summary computation
- Failure modes: HTTP errors, pytest timeouts
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase, TransactionTestCase, override_settings

from audit_runner.scaffold import cleanup_scaffold, create_scaffold
from audits.models import AuditRun, RuleResult
from audits.services import run_audit
from devices.models import Device, DeviceHeader
from rules.models import CustomRule, SimpleRule


# ──────────────────────────────────────────────────────────────────────
# Scaffold tests
# ──────────────────────────────────────────────────────────────────────


class CreateScaffoldTests(TestCase):
    """Tests for audit_runner.scaffold.create_scaffold."""

    def setUp(self):
        self.device = Device.objects.create(
            name="test-router",
            hostname="10.0.0.1",
            api_endpoint="http://10.0.0.1/api/config",
        )
        self.audit_run = AuditRun.objects.create(
            device=self.device,
            status="pending",
            trigger="manual",
        )
        self.config_text = "hostname test-router\ninterface Gig0/0\n ip address 10.0.0.1 255.255.255.0"
        self.simple_rules = [
            {
                "id": 1,
                "name": "check_hostname",
                "rule_type": "must_contain",
                "pattern": "hostname",
                "severity": "high",
            },
            {
                "id": 2,
                "name": "no_telnet",
                "rule_type": "must_not_contain",
                "pattern": "transport input telnet",
                "severity": "critical",
            },
        ]
        self.custom_rules = [
            {
                "filename": "test_ntp.py",
                "content": "def test_ntp(device_config):\n    assert 'ntp server' in device_config\n",
            },
        ]
        self.scaffold_path = None

    def tearDown(self):
        if self.scaffold_path and self.scaffold_path.exists():
            cleanup_scaffold(self.scaffold_path)

    def test_create_scaffold_returns_existing_directory(self):
        """create_scaffold must return a Path to a directory that exists."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        self.assertTrue(self.scaffold_path.exists())
        self.assertTrue(self.scaffold_path.is_dir())

    def test_create_scaffold_directory_name_contains_audit_run_id(self):
        """The temp directory name should include the audit run's id."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        self.assertIn(str(self.audit_run.id), self.scaffold_path.name)

    def test_config_txt_contains_config_text(self):
        """_config.txt must contain the exact config text passed in."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        config_file = self.scaffold_path / "_config.txt"
        self.assertTrue(config_file.exists())
        self.assertEqual(config_file.read_text(), self.config_text)

    def test_rules_json_contains_serialized_rules(self):
        """_rules.json must contain the simple_rules list serialized as JSON."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        rules_file = self.scaffold_path / "_rules.json"
        self.assertTrue(rules_file.exists())
        loaded = json.loads(rules_file.read_text())
        self.assertEqual(loaded, self.simple_rules)

    def test_conftest_py_is_generated(self):
        """conftest.py must exist and contain the device_config fixture."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        conftest_file = self.scaffold_path / "conftest.py"
        self.assertTrue(conftest_file.exists())
        content = conftest_file.read_text()
        self.assertIn("device_config", content)
        self.assertIn("_config.txt", content)
        self.assertIn("_rules.json", content)

    def test_test_simple_rules_py_is_generated(self):
        """test_simple_rules.py must exist when simple_rules are provided."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        test_file = self.scaffold_path / "test_simple_rules.py"
        self.assertTrue(test_file.exists())
        content = test_file.read_text()
        self.assertIn("test_simple_rule", content)

    def test_test_simple_rules_py_not_generated_when_no_rules(self):
        """test_simple_rules.py must NOT exist when simple_rules is empty."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, [], self.custom_rules,
        )
        test_file = self.scaffold_path / "test_simple_rules.py"
        self.assertFalse(test_file.exists())

    def test_custom_rules_placed_in_custom_subdirectory(self):
        """Custom rule files must live inside a custom/ subdirectory."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        custom_dir = self.scaffold_path / "custom"
        self.assertTrue(custom_dir.exists())
        self.assertTrue(custom_dir.is_dir())

        custom_file = custom_dir / "test_ntp.py"
        self.assertTrue(custom_file.exists())
        self.assertEqual(
            custom_file.read_text(),
            "def test_ntp(device_config):\n    assert 'ntp server' in device_config\n",
        )

    def test_custom_conftest_is_generated(self):
        """custom/conftest.py must exist and reference device_config fixture."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, self.custom_rules,
        )
        custom_conftest = self.scaffold_path / "custom" / "conftest.py"
        self.assertTrue(custom_conftest.exists())
        content = custom_conftest.read_text()
        self.assertIn("device_config", content)

    def test_no_custom_dir_when_no_custom_rules(self):
        """The custom/ subdirectory must NOT be created when custom_rules is empty."""
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, [],
        )
        custom_dir = self.scaffold_path / "custom"
        self.assertFalse(custom_dir.exists())

    def test_multiple_custom_rules(self):
        """All custom rule files must be written into the custom/ subdirectory."""
        custom_rules = [
            {"filename": "test_aaa.py", "content": "def test_a(): pass\n"},
            {"filename": "test_bbb.py", "content": "def test_b(): pass\n"},
        ]
        self.scaffold_path = create_scaffold(
            self.audit_run, self.config_text, self.simple_rules, custom_rules,
        )
        custom_dir = self.scaffold_path / "custom"
        self.assertTrue((custom_dir / "test_aaa.py").exists())
        self.assertTrue((custom_dir / "test_bbb.py").exists())
        self.assertEqual(
            (custom_dir / "test_aaa.py").read_text(), "def test_a(): pass\n"
        )
        self.assertEqual(
            (custom_dir / "test_bbb.py").read_text(), "def test_b(): pass\n"
        )


class CleanupScaffoldTests(TestCase):
    """Tests for audit_runner.scaffold.cleanup_scaffold."""

    def test_cleanup_scaffold_removes_directory(self):
        """cleanup_scaffold must remove the given directory entirely."""
        tmp = Path(tempfile.mkdtemp(prefix="netaudit_cleanup_test_"))
        (tmp / "dummy.txt").write_text("hello")
        self.assertTrue(tmp.exists())

        cleanup_scaffold(tmp)

        self.assertFalse(tmp.exists())

    def test_cleanup_scaffold_ignores_nonexistent_path(self):
        """cleanup_scaffold must not raise on a path that does not exist."""
        non_existent = Path(tempfile.gettempdir()) / "netaudit_does_not_exist_xyz"
        # Should not raise
        cleanup_scaffold(non_existent)


# ──────────────────────────────────────────────────────────────────────
# Service tests (run_audit)
# ──────────────────────────────────────────────────────────────────────


def _build_mock_report(simple_rule, custom_rule=None):
    """
    Build a fake pytest-json-report dict with one passing simple-rule test
    and optionally one failing custom-rule test.
    """
    tests = [
        {
            "nodeid": f"test_simple_rules.py::test_simple_rule[rule-{simple_rule.id}-{simple_rule.name}]",
            "outcome": "passed",
            "call": {},
        },
    ]
    summary = {"total": 1, "passed": 1, "failed": 0, "error": 0}

    if custom_rule is not None:
        tests.append(
            {
                "nodeid": f"custom/{custom_rule.filename}::test_custom",
                "outcome": "failed",
                "call": {
                    "longrepr": "AssertionError: expected ntp server in config",
                },
            }
        )
        summary["total"] = 2
        summary["failed"] = 1

    return {"tests": tests, "summary": summary, "exitcode": 0 if not custom_rule else 1}


@override_settings(AUDIT_RUNNER_TIMEOUT=60)
class RunAuditSuccessTests(TransactionTestCase):
    """Test run_audit with a successful HTTP fetch and pytest execution."""

    def setUp(self):
        self.device = Device.objects.create(
            name="core-switch",
            hostname="10.1.1.1",
            api_endpoint="http://10.1.1.1/api/config",
        )
        DeviceHeader.objects.create(
            device=self.device,
            key="Authorization",
            value="Bearer tok123",
        )
        self.simple_rule = SimpleRule.objects.create(
            name="check_ntp",
            rule_type="must_contain",
            pattern="ntp server",
            severity="high",
            device=self.device,
            enabled=True,
        )
        self.custom_rule = CustomRule.objects.create(
            name="NTP custom check",
            filename="test_ntp.py",
            content="def test_custom(device_config):\n    assert 'ntp' in device_config\n",
            severity="critical",
            device=self.device,
            enabled=True,
        )
        self.config_text = "hostname core-switch\nntp server 10.0.0.100"
        self.mock_report = _build_mock_report(self.simple_rule, self.custom_rule)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_status_transitions_to_completed(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """run_audit must transition: pending -> fetching_config -> running_rules -> completed."""
        # -- arrange --
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        observed_statuses = []
        original_save = AuditRun.save

        def spy_save(instance, *args, **kwargs):
            original_save(instance, *args, **kwargs)
            if instance.device_id == self.device.id:
                observed_statuses.append(instance.status)

        # -- act --
        with patch.object(AuditRun, "save", spy_save):
            audit_run_id = run_audit(self.device.id, trigger="manual")

        # -- assert --
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        self.assertEqual(audit_run.status, "completed")

        # The status list must include all intermediate states in order
        self.assertIn("fetching_config", observed_statuses)
        self.assertIn("running_rules", observed_statuses)
        self.assertIn("completed", observed_statuses)

        idx_fetching = observed_statuses.index("fetching_config")
        idx_running = observed_statuses.index("running_rules")
        idx_completed = observed_statuses.index("completed")
        self.assertLess(idx_fetching, idx_running)
        self.assertLess(idx_running, idx_completed)

        # Cleanup
        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_rule_results_created_from_report(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """RuleResult rows must be created from the parsed pytest JSON report."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        results = RuleResult.objects.filter(audit_run_id=audit_run_id)

        # One passed (simple rule) + one failed (custom rule)
        self.assertEqual(results.count(), 2)

        passed = results.get(outcome="passed")
        self.assertEqual(passed.simple_rule_id, self.simple_rule.id)
        self.assertIsNone(passed.custom_rule)
        self.assertEqual(passed.severity, "high")
        self.assertIn(f"rule-{self.simple_rule.id}", passed.test_node_id)

        failed = results.get(outcome="failed")
        self.assertEqual(failed.custom_rule_id, self.custom_rule.id)
        self.assertIsNone(failed.simple_rule)
        self.assertEqual(failed.severity, "critical")
        self.assertIn("custom/test_ntp.py", failed.test_node_id)
        self.assertIn("AssertionError", failed.message)

        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_summary_computed_correctly(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """AuditRun.summary must reflect counts from the pytest JSON report."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.summary["total"], 2)
        self.assertEqual(audit_run.summary["passed"], 1)
        self.assertEqual(audit_run.summary["failed"], 1)
        self.assertEqual(audit_run.summary["error"], 0)

        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_config_snapshot_saved(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """AuditRun.config_snapshot must contain the fetched config text."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        self.assertEqual(audit_run.config_snapshot, self.config_text)

        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_fetch_config_uses_device_headers(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """requests.get must be called with the device's api_endpoint and headers."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        run_audit(self.device.id)

        mock_get.assert_called_once_with(
            "http://10.1.1.1/api/config",
            headers={"Authorization": "Bearer tok123"},
            timeout=30,
        )

        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_pytest_json_report_saved(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """AuditRun.pytest_json_report must store the full JSON report dict."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        self.assertEqual(audit_run.pytest_json_report, self.mock_report)

        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_completed_at_set_on_success(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """AuditRun.completed_at must be set when the run completes successfully."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=1, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        self.assertIsNotNone(audit_run.started_at)
        self.assertIsNotNone(audit_run.completed_at)
        self.assertGreaterEqual(audit_run.completed_at, audit_run.started_at)

        cleanup_scaffold(scaffold_dir)


@override_settings(AUDIT_RUNNER_TIMEOUT=60)
class RunAuditSimpleRuleOnlyTests(TransactionTestCase):
    """Test run_audit when only simple rules exist (no custom rules)."""

    def setUp(self):
        self.device = Device.objects.create(
            name="edge-router",
            hostname="10.2.2.1",
            api_endpoint="http://10.2.2.1/api/config",
        )
        self.simple_rule = SimpleRule.objects.create(
            name="check_acl",
            rule_type="must_contain",
            pattern="access-list",
            severity="medium",
            device=self.device,
            enabled=True,
        )
        self.config_text = "hostname edge-router\naccess-list 100 permit any"
        self.mock_report = _build_mock_report(self.simple_rule)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_only_simple_rule_results(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """When only simple rules exist, only those RuleResults are created."""
        mock_response = Mock()
        mock_response.text = self.config_text
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(self.mock_report))

        mock_subprocess.return_value = Mock(
            returncode=0, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        results = RuleResult.objects.filter(audit_run_id=audit_run_id)

        self.assertEqual(results.count(), 1)
        result = results.first()
        self.assertEqual(result.outcome, "passed")
        self.assertEqual(result.simple_rule_id, self.simple_rule.id)
        self.assertIsNone(result.custom_rule)
        self.assertEqual(result.severity, "medium")

        audit_run = AuditRun.objects.get(pk=audit_run_id)
        self.assertEqual(audit_run.summary["total"], 1)
        self.assertEqual(audit_run.summary["passed"], 1)
        self.assertEqual(audit_run.summary["failed"], 0)

        cleanup_scaffold(scaffold_dir)


@override_settings(AUDIT_RUNNER_TIMEOUT=60)
class RunAuditFailureFetchConfigTests(TransactionTestCase):
    """Test run_audit when fetching device config fails."""

    def setUp(self):
        self.device = Device.objects.create(
            name="unreachable-device",
            hostname="10.99.99.99",
            api_endpoint="http://10.99.99.99/api/config",
        )

    @patch("audits.services.requests.get")
    def test_http_error_sets_status_failed(self, mock_get):
        """If requests.get raises, AuditRun.status must be 'failed'."""
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError(
            "Connection refused"
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.status, "failed")
        self.assertIn("Config fetch failed", audit_run.error_message)
        self.assertIn("Connection refused", audit_run.error_message)

    @patch("audits.services.requests.get")
    def test_http_404_sets_status_failed(self, mock_get):
        """If the server returns a 404, raise_for_status triggers failure."""
        import requests as req

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.status, "failed")
        self.assertIn("Config fetch failed", audit_run.error_message)

    @patch("audits.services.requests.get")
    def test_no_rule_results_on_fetch_failure(self, mock_get):
        """No RuleResult records should be created if config fetch fails."""
        import requests as req

        mock_get.side_effect = req.exceptions.Timeout("timed out")

        audit_run_id = run_audit(self.device.id)
        results = RuleResult.objects.filter(audit_run_id=audit_run_id)
        self.assertEqual(results.count(), 0)

    @patch("audits.services.requests.get")
    def test_started_at_set_even_on_fetch_failure(self, mock_get):
        """started_at must still be set even when config fetch fails."""
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError("refused")

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)
        self.assertIsNotNone(audit_run.started_at)


@override_settings(AUDIT_RUNNER_TIMEOUT=5)
class RunAuditPytestTimeoutTests(TransactionTestCase):
    """Test run_audit when pytest subprocess times out."""

    def setUp(self):
        self.device = Device.objects.create(
            name="slow-device",
            hostname="10.3.3.1",
            api_endpoint="http://10.3.3.1/api/config",
        )
        self.simple_rule = SimpleRule.objects.create(
            name="check_something",
            rule_type="must_contain",
            pattern="something",
            severity="low",
            device=self.device,
            enabled=True,
        )

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_subprocess_timeout_sets_status_failed(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """If subprocess.run raises TimeoutExpired, status must be 'failed'."""
        mock_response = Mock()
        mock_response.text = "hostname slow-device"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["pytest"], timeout=5
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.status, "failed")
        self.assertIn("timed out", audit_run.error_message.lower())

        cleanup_scaffold(scaffold_dir)

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_scaffold_cleaned_up_after_timeout(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """cleanup_scaffold must be called even when pytest times out."""
        mock_response = Mock()
        mock_response.text = "hostname slow-device"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["pytest"], timeout=5
        )

        run_audit(self.device.id)
        mock_cleanup.assert_called_once_with(scaffold_dir)

        cleanup_scaffold(scaffold_dir)


@override_settings(AUDIT_RUNNER_TIMEOUT=60)
class RunAuditNoReportFileTests(TransactionTestCase):
    """Test run_audit when pytest exits but does not produce a report file."""

    def setUp(self):
        self.device = Device.objects.create(
            name="no-report-device",
            hostname="10.4.4.1",
            api_endpoint="http://10.4.4.1/api/config",
        )
        self.simple_rule = SimpleRule.objects.create(
            name="check_dns",
            rule_type="must_contain",
            pattern="ip name-server",
            severity="medium",
            device=self.device,
            enabled=True,
        )

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_missing_report_still_completes(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """When no report.json exists, run_audit completes with an empty summary."""
        mock_response = Mock()
        mock_response.text = "hostname no-report-device"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir
        # Do NOT create report.json in scaffold_dir

        mock_subprocess.return_value = Mock(
            returncode=2, stdout="", stderr=""
        )

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.status, "completed")
        self.assertEqual(audit_run.summary["total"], 0)
        self.assertEqual(audit_run.summary["passed"], 0)
        self.assertEqual(audit_run.summary["failed"], 0)
        self.assertEqual(audit_run.summary["error"], 0)

        results = RuleResult.objects.filter(audit_run_id=audit_run_id)
        self.assertEqual(results.count(), 0)

        cleanup_scaffold(scaffold_dir)


@override_settings(AUDIT_RUNNER_TIMEOUT=60)
class RunAuditGlobalRulesTests(TransactionTestCase):
    """Test that global rules (device=None) are picked up during an audit."""

    def setUp(self):
        self.device = Device.objects.create(
            name="global-rules-device",
            hostname="10.5.5.1",
            api_endpoint="http://10.5.5.1/api/config",
        )
        # Global rule (device=None)
        self.global_rule = SimpleRule.objects.create(
            name="global_ntp",
            rule_type="must_contain",
            pattern="ntp server",
            severity="high",
            device=None,
            enabled=True,
        )
        # Device-specific rule
        self.device_rule = SimpleRule.objects.create(
            name="device_bgp",
            rule_type="must_contain",
            pattern="router bgp",
            severity="critical",
            device=self.device,
            enabled=True,
        )

    @patch("audits.services.cleanup_scaffold")
    @patch("audits.services.create_scaffold")
    @patch("audits.services.subprocess.run")
    @patch("audits.services.requests.get")
    def test_both_global_and_device_rules_used(
        self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup
    ):
        """create_scaffold must receive both global and device-scoped rules."""
        mock_response = Mock()
        mock_response.text = "hostname global-rules-device"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
        mock_create_scaffold.return_value = scaffold_dir

        # Create an empty report so the run completes
        report = {"tests": [], "summary": {"total": 0, "passed": 0, "failed": 0, "error": 0}, "exitcode": 0}
        report_file = scaffold_dir / "report.json"
        report_file.write_text(json.dumps(report))

        mock_subprocess.return_value = Mock(
            returncode=0, stdout="", stderr=""
        )

        run_audit(self.device.id)

        # Verify create_scaffold was called and simple_rules includes both rules
        mock_create_scaffold.assert_called_once()
        call_args = mock_create_scaffold.call_args
        simple_rules_arg = call_args[0][2]  # third positional arg
        rule_ids = {r["id"] for r in simple_rules_arg}

        self.assertIn(self.global_rule.id, rule_ids)
        self.assertIn(self.device_rule.id, rule_ids)

        cleanup_scaffold(scaffold_dir)


@override_settings(AUDIT_RUNNER_TIMEOUT=60)
class RunAuditTriggerTests(TransactionTestCase):
    """Test that the trigger parameter is correctly recorded."""

    def setUp(self):
        self.device = Device.objects.create(
            name="trigger-device",
            hostname="10.6.6.1",
            api_endpoint="http://10.6.6.1/api/config",
        )

    @patch("audits.services.requests.get")
    def test_trigger_recorded_on_audit_run(self, mock_get):
        """The trigger value must be stored on the AuditRun."""
        import requests as req

        # Make it fail quickly at fetch so we don't need to mock subprocess
        mock_get.side_effect = req.exceptions.ConnectionError("fail")

        audit_run_id = run_audit(self.device.id, trigger="scheduled")
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.trigger, "scheduled")

    @patch("audits.services.requests.get")
    def test_default_trigger_is_manual(self, mock_get):
        """The default trigger value must be 'manual'."""
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError("fail")

        audit_run_id = run_audit(self.device.id)
        audit_run = AuditRun.objects.get(pk=audit_run_id)

        self.assertEqual(audit_run.trigger, "manual")
