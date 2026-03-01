from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audits.models import AuditRun, AuditSchedule, RuleResult
from devices.models import Device, DeviceGroup
from rules.models import CustomRule, SimpleRule


# ---------------------------------------------------------------------------
# Helper mixin for creating common test fixtures
# ---------------------------------------------------------------------------
class AuditFixtureMixin:
    """Shared fixture setup for audit tests."""

    def create_device(self, **kwargs):
        defaults = {
            "name": "switch-01",
            "hostname": "192.168.1.1",
            "api_endpoint": "https://192.168.1.1/api",
        }
        defaults.update(kwargs)
        return Device.objects.create(**defaults)

    def create_audit_run(self, device=None, **kwargs):
        if device is None:
            device = self.create_device()
        defaults = {
            "device": device,
            "status": AuditRun.Status.COMPLETED,
            "trigger": AuditRun.Trigger.MANUAL,
        }
        defaults.update(kwargs)
        return AuditRun.objects.create(**defaults)

    def create_simple_rule(self, device=None, **kwargs):
        defaults = {
            "name": "NTP check",
            "rule_type": SimpleRule.RuleType.MUST_CONTAIN,
            "pattern": "ntp server",
        }
        if device is not None:
            defaults["device"] = device
        defaults.update(kwargs)
        return SimpleRule.objects.create(**defaults)

    def create_custom_rule(self, device=None, **kwargs):
        defaults = {
            "name": "Custom NTP test",
            "filename": "test_ntp.py",
            "content": "def test_ntp(): pass",
        }
        if device is not None:
            defaults["device"] = device
        defaults.update(kwargs)
        return CustomRule.objects.create(**defaults)


# ===========================================================================
# MODEL TESTS
# ===========================================================================
class AuditRunModelTests(AuditFixtureMixin, TestCase):
    """Tests for the AuditRun model."""

    def test_create_audit_run_with_defaults(self):
        device = self.create_device()
        run = AuditRun.objects.create(device=device)
        self.assertEqual(run.status, AuditRun.Status.PENDING)
        self.assertEqual(run.trigger, AuditRun.Trigger.MANUAL)
        self.assertEqual(run.config_snapshot, "")
        self.assertIsNone(run.config_fetched_at)
        self.assertIsNone(run.pytest_json_report)
        self.assertIsNone(run.summary)
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.completed_at)
        self.assertEqual(run.error_message, "")
        self.assertIsNotNone(run.created_at)

    def test_create_audit_run_with_all_fields(self):
        device = self.create_device()
        now = timezone.now()
        run = AuditRun.objects.create(
            device=device,
            status=AuditRun.Status.COMPLETED,
            trigger=AuditRun.Trigger.SCHEDULED,
            config_snapshot="hostname switch-01",
            config_fetched_at=now,
            pytest_json_report={"tests": []},
            summary={"passed": 5, "failed": 2, "error": 0},
            started_at=now,
            completed_at=now,
            error_message="",
        )
        run.refresh_from_db()
        self.assertEqual(run.status, AuditRun.Status.COMPLETED)
        self.assertEqual(run.trigger, AuditRun.Trigger.SCHEDULED)
        self.assertEqual(run.config_snapshot, "hostname switch-01")
        self.assertEqual(run.summary, {"passed": 5, "failed": 2, "error": 0})

    def test_str(self):
        device = self.create_device()
        run = AuditRun.objects.create(device=device)
        expected = f"AuditRun {run.pk} - {device} ({run.status})"
        self.assertEqual(str(run), expected)

    def test_ordering_is_newest_first(self):
        device = self.create_device()
        run1 = AuditRun.objects.create(device=device)
        run2 = AuditRun.objects.create(device=device)
        runs = list(AuditRun.objects.all())
        self.assertEqual(runs[0], run2)
        self.assertEqual(runs[1], run1)

    def test_cascade_delete_on_device(self):
        device = self.create_device()
        AuditRun.objects.create(device=device)
        device.delete()
        self.assertEqual(AuditRun.objects.count(), 0)

    def test_status_choices(self):
        expected = {
            "pending",
            "fetching_config",
            "running_rules",
            "completed",
            "failed",
        }
        actual = {choice[0] for choice in AuditRun.Status.choices}
        self.assertEqual(actual, expected)

    def test_trigger_choices(self):
        expected = {"manual", "scheduled"}
        actual = {choice[0] for choice in AuditRun.Trigger.choices}
        self.assertEqual(actual, expected)


class RuleResultModelTests(AuditFixtureMixin, TestCase):
    """Tests for the RuleResult model."""

    def test_create_rule_result_with_simple_rule(self):
        device = self.create_device()
        run = self.create_audit_run(device=device)
        simple_rule = self.create_simple_rule(device=device)
        result = RuleResult.objects.create(
            audit_run=run,
            simple_rule=simple_rule,
            test_node_id="tests/test_ntp.py::test_ntp_server",
            outcome=RuleResult.Outcome.PASSED,
            message="NTP server found",
            duration=0.05,
            severity="high",
        )
        result.refresh_from_db()
        self.assertEqual(result.audit_run, run)
        self.assertEqual(result.simple_rule, simple_rule)
        self.assertIsNone(result.custom_rule)
        self.assertEqual(result.outcome, RuleResult.Outcome.PASSED)
        self.assertEqual(result.severity, "high")

    def test_create_rule_result_with_custom_rule(self):
        device = self.create_device()
        run = self.create_audit_run(device=device)
        custom_rule = self.create_custom_rule(device=device)
        result = RuleResult.objects.create(
            audit_run=run,
            custom_rule=custom_rule,
            test_node_id="tests/test_ntp.py::test_custom",
            outcome=RuleResult.Outcome.FAILED,
            message="Check failed",
        )
        self.assertEqual(result.custom_rule, custom_rule)
        self.assertIsNone(result.simple_rule)

    def test_create_rule_result_no_rule_fk(self):
        """RuleResult can exist with both rule FKs as None."""
        run = self.create_audit_run()
        result = RuleResult.objects.create(
            audit_run=run,
            test_node_id="tests/test_misc.py::test_something",
            outcome=RuleResult.Outcome.ERROR,
        )
        self.assertIsNone(result.simple_rule)
        self.assertIsNone(result.custom_rule)

    def test_str(self):
        run = self.create_audit_run()
        result = RuleResult.objects.create(
            audit_run=run,
            test_node_id="tests/test_ntp.py::test_ntp",
            outcome=RuleResult.Outcome.PASSED,
        )
        self.assertEqual(str(result), "tests/test_ntp.py::test_ntp - passed")

    def test_default_severity(self):
        run = self.create_audit_run()
        result = RuleResult.objects.create(
            audit_run=run,
            test_node_id="tests/test_x.py::test_y",
            outcome=RuleResult.Outcome.SKIPPED,
        )
        self.assertEqual(result.severity, "medium")

    def test_ordering_by_test_node_id(self):
        run = self.create_audit_run()
        r2 = RuleResult.objects.create(
            audit_run=run,
            test_node_id="b_test",
            outcome=RuleResult.Outcome.PASSED,
        )
        r1 = RuleResult.objects.create(
            audit_run=run,
            test_node_id="a_test",
            outcome=RuleResult.Outcome.FAILED,
        )
        results = list(RuleResult.objects.all())
        self.assertEqual(results[0], r1)
        self.assertEqual(results[1], r2)

    def test_cascade_delete_on_audit_run(self):
        run = self.create_audit_run()
        RuleResult.objects.create(
            audit_run=run,
            test_node_id="t",
            outcome=RuleResult.Outcome.PASSED,
        )
        run.delete()
        self.assertEqual(RuleResult.objects.count(), 0)

    def test_set_null_on_simple_rule_delete(self):
        device = self.create_device()
        run = self.create_audit_run(device=device)
        rule = self.create_simple_rule(device=device)
        result = RuleResult.objects.create(
            audit_run=run,
            simple_rule=rule,
            test_node_id="t",
            outcome=RuleResult.Outcome.PASSED,
        )
        rule.delete()
        result.refresh_from_db()
        self.assertIsNone(result.simple_rule)

    def test_set_null_on_custom_rule_delete(self):
        device = self.create_device()
        run = self.create_audit_run(device=device)
        rule = self.create_custom_rule(device=device)
        result = RuleResult.objects.create(
            audit_run=run,
            custom_rule=rule,
            test_node_id="t",
            outcome=RuleResult.Outcome.PASSED,
        )
        rule.delete()
        result.refresh_from_db()
        self.assertIsNone(result.custom_rule)

    def test_outcome_choices(self):
        expected = {"passed", "failed", "error", "skipped"}
        actual = {choice[0] for choice in RuleResult.Outcome.choices}
        self.assertEqual(actual, expected)


class AuditScheduleModelTests(AuditFixtureMixin, TestCase):
    """Tests for the AuditSchedule model."""

    def test_create_schedule(self):
        device = self.create_device()
        schedule = AuditSchedule.objects.create(
            device=device,
            name="Nightly audit",
            cron_expression="0 2 * * *",
        )
        schedule.refresh_from_db()
        self.assertEqual(schedule.name, "Nightly audit")
        self.assertEqual(schedule.cron_expression, "0 2 * * *")
        self.assertTrue(schedule.enabled)
        self.assertIsNone(schedule.django_q_schedule_id)
        self.assertIsNotNone(schedule.created_at)
        self.assertIsNotNone(schedule.updated_at)

    def test_create_schedule_disabled(self):
        device = self.create_device()
        schedule = AuditSchedule.objects.create(
            device=device,
            name="Weekly audit",
            cron_expression="0 0 * * 0",
            enabled=False,
        )
        self.assertFalse(schedule.enabled)

    def test_str(self):
        device = self.create_device()
        schedule = AuditSchedule.objects.create(
            device=device,
            name="Daily audit",
            cron_expression="0 0 * * *",
        )
        self.assertEqual(str(schedule), f"Daily audit ({device})")

    def test_cascade_delete_on_device(self):
        device = self.create_device()
        AuditSchedule.objects.create(
            device=device,
            name="Test",
            cron_expression="* * * * *",
        )
        device.delete()
        self.assertEqual(AuditSchedule.objects.count(), 0)


# ===========================================================================
# API TESTS
# ===========================================================================
class AuditRunAPITests(AuditFixtureMixin, APITestCase):
    """Tests for the AuditRun REST endpoints."""

    def setUp(self):
        self.device = self.create_device()

    # ---- LIST ----
    def test_list_audit_runs_empty(self):
        url = reverse("auditrun-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_list_audit_runs(self):
        self.create_audit_run(device=self.device)
        self.create_audit_run(device=self.device, status=AuditRun.Status.FAILED)
        url = reverse("auditrun-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_audit_runs_contains_device_name(self):
        self.create_audit_run(device=self.device)
        url = reverse("auditrun-list")
        response = self.client.get(url)
        self.assertEqual(response.data["results"][0]["device_name"], self.device.name)

    def test_list_audit_runs_filter_by_status(self):
        self.create_audit_run(device=self.device, status=AuditRun.Status.COMPLETED)
        self.create_audit_run(device=self.device, status=AuditRun.Status.FAILED)
        url = reverse("auditrun-list")
        response = self.client.get(url, {"status": "completed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], "completed")

    def test_list_audit_runs_filter_by_device(self):
        other_device = self.create_device(
            name="switch-02",
            hostname="192.168.1.2",
            api_endpoint="https://192.168.1.2/api",
        )
        self.create_audit_run(device=self.device)
        self.create_audit_run(device=other_device)
        url = reverse("auditrun-list")
        response = self.client.get(url, {"device": self.device.pk})
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_serializer_fields(self):
        self.create_audit_run(device=self.device)
        url = reverse("auditrun-list")
        response = self.client.get(url)
        item = response.data["results"][0]
        expected_fields = {
            "id",
            "device",
            "device_name",
            "status",
            "trigger",
            "summary",
            "started_at",
            "completed_at",
            "created_at",
        }
        self.assertEqual(set(item.keys()), expected_fields)

    # ---- CREATE ----
    @patch("audits.tasks.enqueue_audit")
    def test_create_audit_run(self, mock_enqueue):
        url = reverse("auditrun-list")
        response = self.client.post(url, {"device": self.device.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuditRun.objects.count(), 1)
        run = AuditRun.objects.first()
        self.assertEqual(run.device, self.device)
        self.assertEqual(run.status, AuditRun.Status.PENDING)
        self.assertEqual(run.trigger, AuditRun.Trigger.MANUAL)

    @patch("audits.tasks.enqueue_audit")
    def test_create_audit_run_calls_enqueue(self, mock_enqueue):
        url = reverse("auditrun-list")
        self.client.post(url, {"device": self.device.pk}, format="json")
        mock_enqueue.assert_called_once_with(self.device.id, trigger="manual")

    @patch("audits.tasks.enqueue_audit")
    def test_create_audit_run_returns_detail_serializer(self, mock_enqueue):
        url = reverse("auditrun-list")
        response = self.client.post(url, {"device": self.device.pk}, format="json")
        self.assertIn("results", response.data)
        self.assertIn("error_message", response.data)
        self.assertIn("config_fetched_at", response.data)

    def test_create_audit_run_invalid_device(self):
        url = reverse("auditrun-list")
        response = self.client.post(url, {"device": 99999}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_audit_run_missing_device(self):
        url = reverse("auditrun-list")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- RETRIEVE ----
    def test_retrieve_audit_run(self):
        run = self.create_audit_run(device=self.device)
        url = reverse("auditrun-detail", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], run.pk)
        self.assertEqual(response.data["device_name"], self.device.name)

    def test_retrieve_audit_run_detail_serializer_fields(self):
        run = self.create_audit_run(device=self.device)
        url = reverse("auditrun-detail", kwargs={"pk": run.pk})
        response = self.client.get(url)
        expected_fields = {
            "id",
            "device",
            "device_name",
            "status",
            "trigger",
            "summary",
            "started_at",
            "completed_at",
            "created_at",
            "results",
            "error_message",
            "config_fetched_at",
        }
        self.assertEqual(set(response.data.keys()), expected_fields)

    def test_retrieve_audit_run_includes_results(self):
        run = self.create_audit_run(device=self.device)
        RuleResult.objects.create(
            audit_run=run,
            test_node_id="tests/test_a.py::test_one",
            outcome=RuleResult.Outcome.PASSED,
        )
        url = reverse("auditrun-detail", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["test_node_id"],
            "tests/test_a.py::test_one",
        )

    def test_retrieve_audit_run_not_found(self):
        url = reverse("auditrun-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- RESULTS ACTION ----
    def test_results_action_empty(self):
        run = self.create_audit_run(device=self.device)
        url = reverse("auditrun-results", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_results_action_with_data(self):
        run = self.create_audit_run(device=self.device)
        simple_rule = self.create_simple_rule(device=self.device)
        RuleResult.objects.create(
            audit_run=run,
            simple_rule=simple_rule,
            test_node_id="tests/test_ntp.py::test_ntp",
            outcome=RuleResult.Outcome.PASSED,
            message="OK",
            duration=0.1,
            severity="high",
        )
        RuleResult.objects.create(
            audit_run=run,
            test_node_id="tests/test_dns.py::test_dns",
            outcome=RuleResult.Outcome.FAILED,
            message="DNS not configured",
        )
        url = reverse("auditrun-results", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_results_action_includes_rule_name(self):
        run = self.create_audit_run(device=self.device)
        simple_rule = self.create_simple_rule(device=self.device)
        RuleResult.objects.create(
            audit_run=run,
            simple_rule=simple_rule,
            test_node_id="t",
            outcome=RuleResult.Outcome.PASSED,
        )
        url = reverse("auditrun-results", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.data[0]["rule_name"], simple_rule.name)

    def test_results_action_rule_name_none_when_no_rule(self):
        run = self.create_audit_run(device=self.device)
        RuleResult.objects.create(
            audit_run=run,
            test_node_id="t",
            outcome=RuleResult.Outcome.PASSED,
        )
        url = reverse("auditrun-results", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertIsNone(response.data[0]["rule_name"])

    def test_results_action_rule_name_from_custom_rule(self):
        run = self.create_audit_run(device=self.device)
        custom_rule = self.create_custom_rule(device=self.device)
        RuleResult.objects.create(
            audit_run=run,
            custom_rule=custom_rule,
            test_node_id="t",
            outcome=RuleResult.Outcome.PASSED,
        )
        url = reverse("auditrun-results", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.data[0]["rule_name"], custom_rule.name)

    def test_results_action_not_found(self):
        url = reverse("auditrun-results", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- CONFIG ACTION ----
    def test_config_action_empty_snapshot(self):
        run = self.create_audit_run(device=self.device)
        url = reverse("auditrun-config", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"config": ""})

    def test_config_action_with_snapshot(self):
        config_text = "hostname switch-01\ninterface Vlan1\n ip address 10.0.0.1"
        run = self.create_audit_run(
            device=self.device,
            config_snapshot=config_text,
        )
        url = reverse("auditrun-config", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["config"], config_text)

    def test_config_action_not_found(self):
        url = reverse("auditrun-config", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AuditScheduleAPITests(AuditFixtureMixin, APITestCase):
    """Tests for the AuditSchedule REST endpoints."""

    def setUp(self):
        self.device = self.create_device()

    # ---- LIST ----
    def test_list_schedules_empty(self):
        url = reverse("auditschedule-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_list_schedules(self):
        AuditSchedule.objects.create(
            device=self.device,
            name="Schedule A",
            cron_expression="0 * * * *",
        )
        AuditSchedule.objects.create(
            device=self.device,
            name="Schedule B",
            cron_expression="0 2 * * *",
        )
        url = reverse("auditschedule-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_schedules_filter_by_enabled(self):
        AuditSchedule.objects.create(
            device=self.device,
            name="Enabled",
            cron_expression="0 * * * *",
            enabled=True,
        )
        AuditSchedule.objects.create(
            device=self.device,
            name="Disabled",
            cron_expression="0 2 * * *",
            enabled=False,
        )
        url = reverse("auditschedule-list")
        response = self.client.get(url, {"enabled": "true"})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Enabled")

    def test_list_schedules_filter_by_device(self):
        other_device = self.create_device(
            name="switch-02",
            hostname="192.168.1.2",
            api_endpoint="https://192.168.1.2/api",
        )
        AuditSchedule.objects.create(
            device=self.device,
            name="S1",
            cron_expression="0 * * * *",
        )
        AuditSchedule.objects.create(
            device=other_device,
            name="S2",
            cron_expression="0 * * * *",
        )
        url = reverse("auditschedule-list")
        response = self.client.get(url, {"device": self.device.pk})
        self.assertEqual(len(response.data["results"]), 1)

    # ---- CREATE ----
    @patch("audits.tasks.create_schedule")
    def test_create_schedule(self, mock_create_schedule):
        url = reverse("auditschedule-list")
        data = {
            "device": self.device.pk,
            "name": "Nightly audit",
            "cron_expression": "0 2 * * *",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuditSchedule.objects.count(), 1)
        schedule = AuditSchedule.objects.first()
        self.assertEqual(schedule.name, "Nightly audit")
        self.assertEqual(schedule.cron_expression, "0 2 * * *")
        self.assertTrue(schedule.enabled)

    @patch("audits.tasks.create_schedule")
    def test_create_schedule_calls_task(self, mock_create_schedule):
        url = reverse("auditschedule-list")
        data = {
            "device": self.device.pk,
            "name": "Nightly audit",
            "cron_expression": "0 2 * * *",
        }
        self.client.post(url, data, format="json")
        mock_create_schedule.assert_called_once()
        called_instance = mock_create_schedule.call_args[0][0]
        self.assertIsInstance(called_instance, AuditSchedule)
        self.assertEqual(called_instance.name, "Nightly audit")

    @patch("audits.tasks.create_schedule")
    def test_create_schedule_django_q_id_is_readonly(self, mock_create_schedule):
        url = reverse("auditschedule-list")
        data = {
            "device": self.device.pk,
            "name": "Test",
            "cron_expression": "0 * * * *",
            "django_q_schedule_id": 999,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        schedule = AuditSchedule.objects.first()
        self.assertIsNone(schedule.django_q_schedule_id)

    def test_create_schedule_missing_required_fields(self):
        url = reverse("auditschedule-list")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- RETRIEVE ----
    def test_retrieve_schedule(self):
        schedule = AuditSchedule.objects.create(
            device=self.device,
            name="Test schedule",
            cron_expression="0 0 * * *",
        )
        url = reverse("auditschedule-detail", kwargs={"pk": schedule.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test schedule")
        self.assertEqual(response.data["cron_expression"], "0 0 * * *")

    def test_retrieve_schedule_not_found(self):
        url = reverse("auditschedule-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- UPDATE ----
    @patch("audits.tasks.create_schedule")
    def test_update_schedule(self, mock_create_schedule):
        schedule = AuditSchedule.objects.create(
            device=self.device,
            name="Old name",
            cron_expression="0 0 * * *",
        )
        url = reverse("auditschedule-detail", kwargs={"pk": schedule.pk})
        data = {
            "device": self.device.pk,
            "name": "Updated name",
            "cron_expression": "0 3 * * *",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schedule.refresh_from_db()
        self.assertEqual(schedule.name, "Updated name")
        self.assertEqual(schedule.cron_expression, "0 3 * * *")

    @patch("audits.tasks.create_schedule")
    def test_partial_update_schedule(self, mock_create_schedule):
        schedule = AuditSchedule.objects.create(
            device=self.device,
            name="Original",
            cron_expression="0 0 * * *",
        )
        url = reverse("auditschedule-detail", kwargs={"pk": schedule.pk})
        response = self.client.patch(url, {"enabled": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schedule.refresh_from_db()
        self.assertFalse(schedule.enabled)
        self.assertEqual(schedule.name, "Original")

    # ---- DELETE ----
    @patch("audits.tasks.delete_schedule")
    def test_delete_schedule(self, mock_delete_schedule):
        schedule = AuditSchedule.objects.create(
            device=self.device,
            name="To delete",
            cron_expression="0 0 * * *",
        )
        url = reverse("auditschedule-detail", kwargs={"pk": schedule.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AuditSchedule.objects.count(), 0)

    @patch("audits.tasks.delete_schedule")
    def test_delete_schedule_calls_task(self, mock_delete_schedule):
        schedule = AuditSchedule.objects.create(
            device=self.device,
            name="To delete",
            cron_expression="0 0 * * *",
        )
        url = reverse("auditschedule-detail", kwargs={"pk": schedule.pk})
        self.client.delete(url)
        mock_delete_schedule.assert_called_once()
        called_instance = mock_delete_schedule.call_args[0][0]
        self.assertEqual(called_instance.name, "To delete")

    def test_delete_schedule_not_found(self):
        url = reverse("auditschedule-detail", kwargs={"pk": 99999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DashboardSummaryAPITests(AuditFixtureMixin, APITestCase):
    """Tests for the dashboard summary endpoint."""

    def setUp(self):
        self.device = self.create_device()
        self.url = reverse("dashboard-summary")

    def test_dashboard_summary_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["device_count"], 1)  # setUp creates one
        self.assertEqual(response.data["recent_audit_count"], 0)
        self.assertEqual(response.data["pass_rate"], 0.0)

    def test_dashboard_summary_device_count(self):
        self.create_device(
            name="switch-02",
            hostname="192.168.1.2",
            api_endpoint="https://192.168.1.2/api",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["device_count"], 2)

    def test_dashboard_summary_recent_audit_count(self):
        """Audits created within the last 24 hours should be counted."""
        self.create_audit_run(device=self.device, status=AuditRun.Status.COMPLETED)
        self.create_audit_run(device=self.device, status=AuditRun.Status.PENDING)
        response = self.client.get(self.url)
        self.assertEqual(response.data["recent_audit_count"], 2)

    def test_dashboard_summary_old_audits_not_counted_as_recent(self):
        """Audits older than 24h should not appear in recent_audit_count."""
        run = self.create_audit_run(device=self.device)
        # Manually set created_at to 2 days ago
        AuditRun.objects.filter(pk=run.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["recent_audit_count"], 0)

    def test_dashboard_summary_pass_rate_calculation(self):
        """Pass rate should reflect completed audits within the last 7 days."""
        now = timezone.now()
        self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.COMPLETED,
            completed_at=now,
            summary={"passed": 8, "failed": 2},
        )
        response = self.client.get(self.url)
        # 8 passed out of 10 total = 80.0%
        self.assertEqual(response.data["pass_rate"], 80.0)

    def test_dashboard_summary_pass_rate_multiple_audits(self):
        now = timezone.now()
        self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.COMPLETED,
            completed_at=now,
            summary={"passed": 5, "failed": 5},
        )
        self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.COMPLETED,
            completed_at=now,
            summary={"passed": 10, "failed": 0},
        )
        response = self.client.get(self.url)
        # 15 passed out of 20 total = 75.0%
        self.assertEqual(response.data["pass_rate"], 75.0)

    def test_dashboard_summary_pass_rate_excludes_non_completed(self):
        """Only COMPLETED audits contribute to pass_rate."""
        now = timezone.now()
        self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.COMPLETED,
            completed_at=now,
            summary={"passed": 10, "failed": 0},
        )
        self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.FAILED,
            summary={"passed": 0, "failed": 10},
        )
        response = self.client.get(self.url)
        # Only the completed audit counts: 10/10 = 100%
        self.assertEqual(response.data["pass_rate"], 100.0)

    def test_dashboard_summary_pass_rate_excludes_old_completed(self):
        """Completed audits older than 7 days should not affect pass_rate."""
        now = timezone.now()
        run = self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.COMPLETED,
            completed_at=now - timedelta(days=10),
            summary={"passed": 0, "failed": 10},
        )
        # Also move completed_at back so the filter excludes it
        AuditRun.objects.filter(pk=run.pk).update(
            completed_at=now - timedelta(days=10),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["pass_rate"], 0.0)

    def test_dashboard_summary_pass_rate_zero_when_no_tests(self):
        """If completed audits have no summary, pass_rate should be 0."""
        now = timezone.now()
        self.create_audit_run(
            device=self.device,
            status=AuditRun.Status.COMPLETED,
            completed_at=now,
            summary=None,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["pass_rate"], 0.0)

    def test_dashboard_summary_response_keys(self):
        response = self.client.get(self.url)
        expected_keys = {"device_count", "recent_audit_count", "pass_rate"}
        self.assertEqual(set(response.data.keys()), expected_keys)


# ===========================================================================
# GROUP-SCOPED RULE GATHERING TESTS
# ===========================================================================
class GroupScopedRuleGatheringTests(AuditFixtureMixin, TestCase):
    """Tests that audit service gathers rules from device groups."""

    def setUp(self):
        self.device = self.create_device()
        self.group = DeviceGroup.objects.create(name="Edge Routers")
        self.device.groups.add(self.group)

    def test_gather_simple_rules_from_group(self):
        """A simple rule scoped to a group should apply to devices in that group."""
        group_rule = SimpleRule.objects.create(
            name="Group NTP",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp server",
            group=self.group,
            enabled=True,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        rule_ids = [r["id"] for r in rules]
        self.assertIn(group_rule.id, rule_ids)

    def test_gather_simple_rules_excludes_other_groups(self):
        """A simple rule scoped to a different group should NOT apply."""
        other_group = DeviceGroup.objects.create(name="Other")
        SimpleRule.objects.create(
            name="Other Group Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=other_group,
            enabled=True,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        self.assertEqual(len(rules), 0)

    def test_gather_simple_rules_union_device_group_global(self):
        """Device gets rules from its own FK, all its groups, and global."""
        device_rule = SimpleRule.objects.create(
            name="Device Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="hostname",
            device=self.device,
            enabled=True,
        )
        group_rule = SimpleRule.objects.create(
            name="Group Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=self.group,
            enabled=True,
        )
        global_rule = SimpleRule.objects.create(
            name="Global Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="logging",
            enabled=True,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        rule_ids = {r["id"] for r in rules}
        self.assertEqual(rule_ids, {device_rule.id, group_rule.id, global_rule.id})

    def test_gather_custom_rules_from_group(self):
        """A custom rule scoped to a group should apply to devices in that group."""
        group_rule = CustomRule.objects.create(
            name="Group Custom",
            filename="test_group.py",
            content="def test_x(): pass",
            group=self.group,
            enabled=True,
        )
        from audits.services import _gather_custom_rules
        rules = _gather_custom_rules(self.device)
        rule_ids = [r["id"] for r in rules]
        self.assertIn(group_rule.id, rule_ids)

    def test_gather_rules_disabled_group_rule_excluded(self):
        """Disabled group rules should not be gathered."""
        SimpleRule.objects.create(
            name="Disabled Group Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=self.group,
            enabled=False,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        self.assertEqual(len(rules), 0)
