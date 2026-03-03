"""
Slack webhook notifications for audit failures.

Sends a summary message to a configured Slack channel when an audit
completes with at least one failed rule.
"""

import logging

import requests

from settings.models import SiteSettings

logger = logging.getLogger(__name__)


def send_slack_notification(audit_run):
    """
    Post a Slack message summarizing audit failures.

    Parameters
    ----------
    audit_run : AuditRun
        A completed audit run with a populated ``summary`` dict.

    Returns
    -------
    bool
        True if the message was sent, False otherwise.
    """
    site_settings = SiteSettings.load()
    webhook_url = site_settings.slack_webhook_url

    if not webhook_url:
        logger.debug("No Slack webhook URL configured; skipping notification.")
        return False

    summary = audit_run.summary or {}
    total = summary.get("total", 0)
    failed = summary.get("failed", 0)
    error = summary.get("error", 0)
    device_name = audit_run.device.name

    # Build severity breakdown from rule results
    from audits.models import RuleResult

    failed_results = RuleResult.objects.filter(
        audit_run=audit_run, outcome="failed"
    )
    severity_counts = {}
    for result in failed_results:
        severity_counts[result.severity] = (
            severity_counts.get(result.severity, 0) + 1
        )

    severity_parts = [
        f"{count} {sev}" for sev, count in sorted(severity_counts.items())
    ]
    severity_text = f" ({', '.join(severity_parts)})" if severity_parts else ""

    completed_at = ""
    if audit_run.completed_at:
        completed_at = audit_run.completed_at.strftime("%Y-%m-%d %H:%M UTC")

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":red_circle: *Audit Failed: {device_name}*\n"
                        f"{failed} of {total} rules failed{severity_text}\n"
                        f"Completed: {completed_at}"
                    ),
                },
            },
        ],
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(
            "Slack notification sent for audit %s on device %s",
            audit_run.id,
            device_name,
        )
        return True
    except requests.RequestException:
        logger.exception(
            "Failed to send Slack notification for audit %s", audit_run.id
        )
        return False


def send_test_slack_notification(webhook_url):
    """
    Send a test message to verify Slack webhook connectivity.

    Parameters
    ----------
    webhook_url : str
        The webhook URL to test.

    Returns
    -------
    bool
        True if the message was sent successfully.
    """
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":white_check_mark: *NetAudit Slack Integration Test*\n"
                        "This is a test notification. "
                        "If you see this, your webhook is configured correctly."
                    ),
                },
            },
        ],
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Test Slack notification failed for %s", webhook_url)
        return False
