import logging
from datetime import datetime, timezone

import requests

from notifications.models import WebhookProvider

logger = logging.getLogger(__name__)


def dispatch_webhooks(audit_run):
    """
    Send webhook notifications for a completed audit run.

    Queries all enabled WebhookProvider instances and fires HTTP POST
    requests based on each provider's trigger_mode. Failures are logged
    but do not affect the audit run status.
    """
    providers = WebhookProvider.objects.filter(enabled=True).prefetch_related("headers")
    if not providers.exists():
        return

    failed_results = audit_run.results.filter(outcome="failed")
    if not failed_results.exists():
        return

    device = audit_run.device
    device_payload = _build_device_payload(device)

    for provider in providers:
        try:
            if provider.trigger_mode == "per_audit":
                _dispatch_per_audit(provider, audit_run, device_payload, failed_results)
            else:
                _dispatch_per_rule(provider, audit_run, device_payload, failed_results)
        except Exception:
            logger.exception(
                "Webhook dispatch failed for provider '%s' (id=%d)",
                provider.name,
                provider.id,
            )


def _build_device_payload(device):
    """Build the device section of the webhook payload."""
    return {
        "id": device.id,
        "name": device.name,
        "hostname": device.hostname,
        "groups": list(device.groups.values_list("name", flat=True)),
    }


def _build_rule_payload(result):
    """Build a single rule failure payload from a RuleResult."""
    rule_name = None
    rule_type = None
    if result.simple_rule:
        rule_name = result.simple_rule.name
        rule_type = "simple"
    elif result.custom_rule:
        rule_name = result.custom_rule.name
        rule_type = "custom"

    return {
        "rule_name": rule_name,
        "rule_type": rule_type,
        "severity": result.severity,
        "message": result.message,
    }


def _get_headers(provider):
    """Build HTTP headers dict from provider's configured headers."""
    headers = {h.key: h.value for h in provider.headers.all()}
    headers["Content-Type"] = "application/json"
    return headers


def _dispatch_per_audit(provider, audit_run, device_payload, failed_results):
    """Send a single webhook with all failures summarized."""
    payload = {
        "event": "audit.completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_run_id": audit_run.id,
        "device": device_payload,
        "summary": audit_run.summary,
        "failed_rules": [_build_rule_payload(r) for r in failed_results],
    }
    _send(provider, payload)


def _dispatch_per_rule(provider, audit_run, device_payload, failed_results):
    """Send one webhook per failed rule."""
    for result in failed_results:
        payload = {
            "event": "rule.failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_run_id": audit_run.id,
            "device": device_payload,
            "rule": _build_rule_payload(result),
        }
        _send(provider, payload)


def _send(provider, payload):
    """Fire the HTTP POST and log the outcome."""
    headers = _get_headers(provider)
    try:
        response = requests.post(
            provider.url, json=payload, headers=headers, timeout=10,
        )
        logger.info(
            "Webhook '%s' responded %d for audit_run %d",
            provider.name,
            response.status_code,
            payload["audit_run_id"],
        )
    except requests.RequestException as exc:
        logger.warning(
            "Webhook '%s' failed: %s",
            provider.name,
            exc,
        )
