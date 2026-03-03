# Webhook Notifications Design

## Problem

When audit rules fail, there's no way to automatically notify external systems for remediation. Users need to manually check audit results and take action.

## Solution

A new `notifications` Django app with a webhook provider model. When an audit completes with failures, NetAudit fires HTTP POST requests to configured webhook endpoints with device info, device IP, and failed rule details.

## Models

### WebhookProvider

| Field | Type | Description |
|-------|------|-------------|
| name | CharField(255) | Display name, e.g. "Remediation API" |
| url | URLField | Endpoint to POST to |
| enabled | BooleanField | Toggle on/off |
| trigger_mode | CharField choices | `per_audit` or `per_rule` |
| created_at | DateTimeField auto | |
| updated_at | DateTimeField auto | |

### WebhookHeader

| Field | Type | Description |
|-------|------|-------------|
| provider | FK(WebhookProvider) | Parent provider |
| key | CharField(255) | Header name, e.g. "Authorization" |
| value | CharField(1024) | Header value, e.g. "Bearer abc123" |

Mirrors the existing `Device`/`DeviceHeader` pattern.

No abstract base class yet (YAGNI) — extract when Slack provider is added.

## Webhook Payloads

### Per-Audit (`trigger_mode = "per_audit"`)

One POST after audit completes, summarizing all failures:

```json
{
  "event": "audit.completed",
  "timestamp": "2026-03-02T12:00:00Z",
  "audit_run_id": 42,
  "device": {
    "id": 1,
    "name": "core-switch-01",
    "hostname": "10.0.1.1",
    "groups": ["datacenter-a", "switches"]
  },
  "summary": { "total": 10, "passed": 7, "failed": 3, "error": 0 },
  "failed_rules": [
    {
      "rule_name": "NTP must be configured",
      "rule_type": "simple",
      "severity": "high",
      "message": "Pattern 'ntp server' not found in config"
    }
  ]
}
```

### Per-Rule (`trigger_mode = "per_rule"`)

One POST per failed rule:

```json
{
  "event": "rule.failed",
  "timestamp": "2026-03-02T12:00:00Z",
  "audit_run_id": 42,
  "device": {
    "id": 1,
    "name": "core-switch-01",
    "hostname": "10.0.1.1",
    "groups": ["datacenter-a", "switches"]
  },
  "rule": {
    "rule_name": "NTP must be configured",
    "rule_type": "simple",
    "severity": "high",
    "message": "Pattern 'ntp server' not found in config"
  }
}
```

## Integration Point

`dispatch_webhooks(audit_run)` is called at the end of `run_audit()` in `audits/services.py`, after the audit is marked completed.

- Queries all enabled `WebhookProvider` instances
- Builds payload per provider's `trigger_mode`
- Fires HTTP POST with configured headers + `Content-Type: application/json`
- Fire-and-forget: failures are logged but don't affect audit status
- Timeout: 10 seconds per request

## API Endpoints

Under `/api/v1/notifications/`:

| Method | Path | Action |
|--------|------|--------|
| GET | `/webhooks/` | List providers |
| POST | `/webhooks/` | Create (with nested headers) |
| GET | `/webhooks/:id/` | Detail |
| PUT/PATCH | `/webhooks/:id/` | Update |
| DELETE | `/webhooks/:id/` | Delete |
| POST | `/webhooks/:id/test/` | Send test payload |

## Frontend

New "Webhooks" card on the Settings page:

- Table listing providers: name, URL, trigger mode, enabled toggle
- "Add Webhook" button → form with name, URL, trigger mode dropdown, key/value header rows
- Edit/delete per provider
- "Test" button sends a sample payload to verify connectivity
- Uses existing shadcn/ui components (Card, Table, Input, Select, Switch, Button)

## Decisions

- No abstract NotificationProvider base — YAGNI until Slack is needed
- Fire-and-forget — webhook failures don't block or fail the audit
- Headers stored as separate rows (not JSON) — matches Device/DeviceHeader pattern
- Content-Type always `application/json` (added automatically, not user-configurable)
