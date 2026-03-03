# Slack Webhook Notifications on Audit Failure

## Overview

Add Slack webhook notification support so that when an audit completes with
at least one failed rule, a summary message is posted to a configured Slack
channel.

## Trigger

A notification fires when an audit reaches `completed` status and
`summary["failed"] > 0`. Audit-level failures (config fetch errors, pytest
crashes) do not trigger notifications.

## Configuration

The Slack webhook URL is stored on the existing `SiteSettings` singleton model
as a new optional `slack_webhook_url` field. No environment variable fallback.

## Architecture

**Approach: direct call inside `run_audit`.** The audit already executes inside
a Django-Q async worker, so a synchronous HTTP POST to Slack at the end of
`run_audit()` is simple and adds no user-facing latency.

Alternatives considered and rejected:
- Django signal on `AuditRun` post-save — over-engineered, signal-based side
  effects are harder to reason about.
- Separate Django-Q task — double-queuing adds complexity for minimal benefit
  when the audit is already async.

## Backend Changes

1. **`SiteSettings` model** — add `slack_webhook_url = URLField(blank=True, default="")`.
2. **Migration** — for the new field.
3. **`SiteSettingsSerializer`** — include `slack_webhook_url` in fields.
4. **New module `backend/audits/notifications.py`** — `send_slack_notification(audit_run)`:
   - Loads `SiteSettings.load()` for the webhook URL.
   - Returns early if URL is empty.
   - POSTs a Slack Block Kit message with: device name, pass/fail/error counts,
     timestamp.
   - Catches and logs HTTP errors (never crashes the audit).
5. **`run_audit()` in `services.py`** — after finalization (line 148), call
   `send_slack_notification(audit_run)` when `summary["failed"] > 0`.
6. **New endpoint `POST /api/settings/test-slack/`** — sends a test
   notification to verify webhook connectivity.

## Frontend Changes

7. **`SiteSettings` type** — add `slack_webhook_url: string`.
8. **Settings page** — add a "Notifications" card below existing settings with:
   - Slack webhook URL input field.
   - "Test" button that calls the test endpoint and shows success/failure toast.

## Slack Message Format

Summary only — no individual rule details:

```
Audit Failed: router-01
3 of 10 rules failed (2 critical, 1 high)
Completed: 2026-03-02 14:30 UTC
```

Uses Slack Block Kit for structured formatting.

## Error Handling

- Notification failures are logged but never cause the audit to fail.
- The `send_slack_notification` function wraps the HTTP call in a try/except.
- Test endpoint returns success/failure status to the frontend.
