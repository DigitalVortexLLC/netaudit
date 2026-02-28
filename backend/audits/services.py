"""
Audit execution service.

Orchestrates the full lifecycle of an audit run: fetching device configuration,
scaffolding a temporary pytest project, executing tests, and parsing results
back into the database.
"""

import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.db.models import Q

from audit_runner.scaffold import cleanup_scaffold, create_scaffold
from audits.models import AuditRun, RuleResult
from devices.models import Device
from rules.models import CustomRule, SimpleRule

logger = logging.getLogger(__name__)


def run_audit(device_id, trigger="manual"):
    """
    Execute a full audit for the given device.

    Parameters
    ----------
    device_id : int
        Primary key of the :class:`~devices.models.Device` to audit.
    trigger : str
        What initiated the audit (``"manual"``, ``"scheduled"``, etc.).

    Returns
    -------
    int
        The primary key of the created :class:`AuditRun`.
    """
    device = Device.objects.get(pk=device_id)
    audit_run = AuditRun.objects.create(
        device=device,
        trigger=trigger,
        status="pending",
    )

    scaffold_path = None

    try:
        # ----------------------------------------------------------
        # 1. Fetch device configuration
        # ----------------------------------------------------------
        audit_run.status = "fetching_config"
        audit_run.started_at = datetime.now(timezone.utc)
        audit_run.save(update_fields=["status", "started_at"])

        try:
            config_text = _fetch_config(device)
        except Exception as exc:
            audit_run.status = "failed"
            audit_run.error_message = f"Config fetch failed: {exc}"
            audit_run.save(update_fields=["status", "error_message"])
            return audit_run.id

        audit_run.config_snapshot = config_text
        audit_run.config_fetched_at = datetime.now(timezone.utc)
        audit_run.save(update_fields=["config_snapshot", "config_fetched_at"])

        # ----------------------------------------------------------
        # 2. Gather applicable rules
        # ----------------------------------------------------------
        simple_rules = list(
            SimpleRule.objects.filter(
                Q(device=device) | Q(device__isnull=True),
                enabled=True,
            ).values("id", "name", "rule_type", "pattern", "severity")
        )

        custom_rules = list(
            CustomRule.objects.filter(
                Q(device=device) | Q(device__isnull=True),
                enabled=True,
            ).values("id", "filename", "content", "name", "severity")
        )

        # ----------------------------------------------------------
        # 3. Build scaffold and run pytest
        # ----------------------------------------------------------
        audit_run.status = "running_rules"
        audit_run.save(update_fields=["status"])

        scaffold_path = create_scaffold(
            audit_run, config_text, simple_rules, custom_rules
        )

        report_file = scaffold_path / "report.json"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(scaffold_path),
                "--json-report",
                f"--json-report-file={report_file}",
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            timeout=getattr(settings, "AUDIT_RUNNER_TIMEOUT", 300),
        )

        logger.debug(
            "pytest stdout:\n%s\npytest stderr:\n%s",
            result.stdout,
            result.stderr,
        )

        # ----------------------------------------------------------
        # 4. Parse results
        # ----------------------------------------------------------
        if report_file.exists():
            report = json.loads(report_file.read_text())
        else:
            report = {
                "tests": [],
                "summary": {},
                "exitcode": result.returncode,
            }

        audit_run.pytest_json_report = report
        audit_run.save(update_fields=["pytest_json_report"])

        _parse_results(audit_run, report, device)

        # ----------------------------------------------------------
        # 5. Finalize
        # ----------------------------------------------------------
        summary = report.get("summary", {})
        audit_run.summary = {
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "error": summary.get("error", 0),
        }
        audit_run.status = "completed"
        audit_run.completed_at = datetime.now(timezone.utc)
        audit_run.save(
            update_fields=[
                "summary",
                "status",
                "completed_at",
            ]
        )

    except Exception as exc:
        logger.exception("Audit run %s failed", audit_run.id)
        audit_run.status = "failed"
        audit_run.error_message = str(exc)
        audit_run.save(update_fields=["status", "error_message"])
    finally:
        if scaffold_path is not None:
            cleanup_scaffold(scaffold_path)

    return audit_run.id


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _fetch_config(device):
    """
    Retrieve the device configuration via HTTP GET.

    Parameters
    ----------
    device : Device
        The device whose ``api_endpoint`` will be queried.

    Returns
    -------
    str
        The raw configuration text.

    Raises
    ------
    requests.RequestException
        On any HTTP or connection error.
    """
    headers = {h.key: h.value for h in device.headers.all()}

    response = requests.get(
        device.api_endpoint,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _parse_results(audit_run, report, device):
    """
    Walk the pytest JSON report and create :class:`RuleResult` rows.

    Parameters
    ----------
    audit_run : AuditRun
        The parent audit run.
    report : dict
        The deserialized ``report.json`` produced by pytest-json-report.
    device : Device
        The device under audit (used for custom rule lookup).
    """
    rule_results = []

    for test in report.get("tests", []):
        node_id = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")

        # Determine failure message (if any)
        message = ""
        call_info = test.get("call", {})
        if outcome == "failed" and call_info:
            longrepr = call_info.get("longrepr", "")
            message = longrepr if isinstance(longrepr, str) else str(longrepr)

        # Try to match to a SimpleRule
        simple_rule_id = _match_simple_rule_id(node_id)
        # Try to match to a CustomRule
        custom_rule = _match_custom_rule(node_id, device)

        # Determine severity from the matched rule
        severity = "medium"
        if simple_rule_id is not None:
            try:
                sr = SimpleRule.objects.get(pk=simple_rule_id)
                severity = sr.severity
            except SimpleRule.DoesNotExist:
                pass
        elif custom_rule is not None:
            severity = custom_rule.severity

        rule_results.append(
            RuleResult(
                audit_run=audit_run,
                test_node_id=node_id,
                outcome=outcome,
                message=message,
                simple_rule_id=simple_rule_id,
                custom_rule=custom_rule,
                severity=severity,
            )
        )

    if rule_results:
        RuleResult.objects.bulk_create(rule_results)


def _match_simple_rule_id(node_id):
    """
    Extract the SimpleRule primary key from a pytest node ID.

    The conftest parametrizes tests with IDs like
    ``test_simple_rules.py::test_simple_rule[rule-42-check_ntp]``.

    Parameters
    ----------
    node_id : str
        The pytest ``nodeid`` string.

    Returns
    -------
    int or None
        The matched rule ID, or ``None`` if no match is found.
    """
    match = re.search(r"rule-(\d+)-", node_id)
    if match:
        return int(match.group(1))
    return None


def _match_custom_rule(node_id, device):
    """
    Match a pytest node ID back to a :class:`~rules.models.CustomRule`.

    Custom tests live under ``custom/<filename>::<test_name>``, so the
    filename is extracted and looked up against enabled rules.

    Parameters
    ----------
    node_id : str
        The pytest ``nodeid`` string.
    device : Device
        The device under audit.

    Returns
    -------
    CustomRule or None
        The matched custom rule, or ``None``.
    """
    match = re.search(r"custom/([^:]+)", node_id)
    if not match:
        return None

    filename = match.group(1)
    try:
        return CustomRule.objects.get(
            Q(device=device) | Q(device__isnull=True),
            filename=filename,
            enabled=True,
        )
    except (CustomRule.DoesNotExist, CustomRule.MultipleObjectsReturned):
        return None
