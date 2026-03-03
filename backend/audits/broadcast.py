"""
Broadcast helpers for sending audit updates over WebSocket.

These functions are called from the synchronous audit service (which runs
in the Django-Q2 worker process).  They use ``async_to_sync`` to push
messages through the Redis-backed channel layer so that connected
WebSocket clients receive real-time updates.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _send_to_group(group_name, message_type, data):
    """Send a message to a channel layer group, swallowing errors."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": message_type, "data": data},
        )
    except Exception:
        logger.debug("Failed to broadcast to %s", group_name, exc_info=True)


def broadcast_audit_status(audit_run):
    """
    Broadcast an audit status change to both the dashboard group
    and the audit-specific detail group.
    """
    data = {
        "type": "audit_status",
        "audit_id": audit_run.id,
        "device_id": audit_run.device_id,
        "device_name": audit_run.device.name,
        "status": audit_run.status,
        "trigger": audit_run.trigger,
        "started_at": (
            audit_run.started_at.isoformat() if audit_run.started_at else None
        ),
        "completed_at": (
            audit_run.completed_at.isoformat() if audit_run.completed_at else None
        ),
        "summary": audit_run.summary,
        "error_message": audit_run.error_message or None,
    }

    # Notify the audit detail page
    _send_to_group(f"audit_{audit_run.id}", "audit_status", data)

    # Notify the dashboard
    _send_to_group("dashboard", "audit_update", data)


def broadcast_rule_result(audit_run, rule_result):
    """
    Broadcast an individual rule result to the audit detail group.
    """
    data = {
        "type": "audit_result",
        "audit_id": audit_run.id,
        "result": {
            "id": rule_result.id,
            "test_node_id": rule_result.test_node_id,
            "outcome": rule_result.outcome,
            "message": rule_result.message,
            "severity": rule_result.severity,
            "rule_name": _get_rule_name(rule_result),
            "duration": rule_result.duration,
        },
    }

    _send_to_group(f"audit_{audit_run.id}", "audit_result", data)


def _get_rule_name(rule_result):
    """Extract the rule name from a RuleResult."""
    if rule_result.simple_rule_id:
        try:
            return rule_result.simple_rule.name
        except Exception:
            return None
    if rule_result.custom_rule_id:
        try:
            return rule_result.custom_rule.name
        except Exception:
            return None
    return None
