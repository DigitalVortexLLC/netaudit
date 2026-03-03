# Slack Webhook Notifications Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Post a Slack notification when an audit completes with at least one failed rule.

**Architecture:** Add `slack_webhook_url` to the existing `SiteSettings` singleton model. A new `notifications.py` module in the audits app sends Slack Block Kit messages via `requests.post`. Called directly from `run_audit()` after finalization. Frontend gets a new Notifications card on the settings page with a test button.

**Tech Stack:** Django, Django REST Framework, requests, React, TanStack Query, shadcn/ui, Sonner toasts

---

### Task 1: Add `slack_webhook_url` to SiteSettings Model

**Files:**
- Modify: `backend/settings/models.py`
- Create: migration via `makemigrations`

**Step 1: Add the field to the model**

In `backend/settings/models.py`, add after `default_api_endpoint`:

```python
slack_webhook_url = models.URLField(
    blank=True,
    default="",
    help_text="Slack incoming webhook URL for audit failure notifications.",
)
```

**Step 2: Create the migration**

Run: `python backend/manage.py makemigrations settings`
Expected: creates a new migration file adding `slack_webhook_url`

**Step 3: Apply the migration**

Run: `python backend/manage.py migrate settings`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/settings/models.py backend/settings/migrations/
git commit -m "feat: add slack_webhook_url field to SiteSettings"
```

---

### Task 2: Update Serializer and Add Tests for the New Field

**Files:**
- Modify: `backend/settings/serializers.py`
- Modify: `backend/settings/tests.py`

**Step 1: Write failing tests**

Add to `SiteSettingsModelTests` in `backend/settings/tests.py`:

```python
def test_slack_webhook_url_blank_by_default(self):
    settings = SiteSettings.load()
    self.assertEqual(settings.slack_webhook_url, "")
```

Add to `SiteSettingsAPITests`:

```python
def test_patch_slack_webhook_url(self):
    url = reverse("site-settings")
    response = self.client.patch(
        url,
        {"slack_webhook_url": "https://hooks.slack.com/services/T00/B00/xxx"},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(
        response.data["slack_webhook_url"],
        "https://hooks.slack.com/services/T00/B00/xxx",
    )

def test_get_settings_includes_slack_webhook_url(self):
    url = reverse("site-settings")
    response = self.client.get(url)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn("slack_webhook_url", response.data)
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/settings/tests.py -v -k "slack"`
Expected: FAIL — serializer doesn't include `slack_webhook_url` yet

**Step 3: Update the serializer**

In `backend/settings/serializers.py`, change fields to:

```python
fields = ["default_api_endpoint", "slack_webhook_url"]
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest backend/settings/tests.py -v -k "slack"`
Expected: all 3 new tests PASS

**Step 5: Commit**

```bash
git add backend/settings/serializers.py backend/settings/tests.py
git commit -m "feat: expose slack_webhook_url in settings API"
```

---

### Task 3: Create the Slack Notification Module

**Files:**
- Create: `backend/audits/notifications.py`

**Step 1: Write the notification module**

Create `backend/audits/notifications.py`:

```python
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
```

**Step 2: Commit**

```bash
git add backend/audits/notifications.py
git commit -m "feat: add Slack notification module for audit failures"
```

---

### Task 4: Write Tests for the Notification Module

**Files:**
- Create: `backend/audits/test_notifications.py`

**Step 1: Write the tests**

Create `backend/audits/test_notifications.py`:

```python
"""Tests for audits.notifications Slack webhook integration."""

from unittest.mock import Mock, patch

from django.test import TestCase

from audits.models import AuditRun, RuleResult
from audits.notifications import send_slack_notification, send_test_slack_notification
from devices.models import Device
from rules.models import SimpleRule
from settings.models import SiteSettings


class SendSlackNotificationTests(TestCase):
    """Tests for send_slack_notification."""

    def setUp(self):
        self.device = Device.objects.create(
            name="core-router",
            hostname="10.0.0.1",
        )
        self.audit_run = AuditRun.objects.create(
            device=self.device,
            status="completed",
            trigger="manual",
            summary={"total": 5, "passed": 3, "failed": 2, "error": 0},
        )
        self.rule = SimpleRule.objects.create(
            name="check_ntp",
            rule_type="must_contain",
            pattern="ntp server",
            severity="critical",
            device=self.device,
            enabled=True,
        )
        RuleResult.objects.create(
            audit_run=self.audit_run,
            test_node_id="test_simple_rules.py::test_check_ntp",
            outcome="failed",
            message="ntp server not found",
            simple_rule=self.rule,
            severity="critical",
        )

    def test_returns_false_when_no_webhook_configured(self):
        result = send_slack_notification(self.audit_run)
        self.assertFalse(result)

    @patch("audits.notifications.requests.post")
    def test_sends_notification_when_webhook_configured(self, mock_post):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={"slack_webhook_url": "https://hooks.slack.com/test"},
        )
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()

        result = send_slack_notification(self.audit_run)

        self.assertTrue(result)
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        text = payload["blocks"][0]["text"]["text"]
        self.assertIn("core-router", text)
        self.assertIn("2 of 5", text)

    @patch("audits.notifications.requests.post")
    def test_includes_severity_breakdown(self, mock_post):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={"slack_webhook_url": "https://hooks.slack.com/test"},
        )
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()

        send_slack_notification(self.audit_run)

        payload = mock_post.call_args[1]["json"]
        text = payload["blocks"][0]["text"]["text"]
        self.assertIn("critical", text)

    @patch("audits.notifications.requests.post")
    def test_returns_false_on_request_error(self, mock_post):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={"slack_webhook_url": "https://hooks.slack.com/test"},
        )
        import requests
        mock_post.side_effect = requests.RequestException("connection failed")

        result = send_slack_notification(self.audit_run)

        self.assertFalse(result)

    @patch("audits.notifications.requests.post")
    def test_does_not_crash_audit_on_failure(self, mock_post):
        """Notification errors must not propagate."""
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={"slack_webhook_url": "https://hooks.slack.com/test"},
        )
        import requests
        mock_post.side_effect = requests.RequestException("timeout")

        # Should not raise
        result = send_slack_notification(self.audit_run)
        self.assertFalse(result)


class SendTestSlackNotificationTests(TestCase):
    """Tests for send_test_slack_notification."""

    @patch("audits.notifications.requests.post")
    def test_sends_test_message(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()

        result = send_test_slack_notification("https://hooks.slack.com/test")

        self.assertTrue(result)
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        text = payload["blocks"][0]["text"]["text"]
        self.assertIn("Test", text)

    @patch("audits.notifications.requests.post")
    def test_returns_false_on_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("fail")

        result = send_test_slack_notification("https://hooks.slack.com/bad")
        self.assertFalse(result)
```

**Step 2: Run the tests**

Run: `python -m pytest backend/audits/test_notifications.py -v`
Expected: all 7 tests PASS

**Step 3: Commit**

```bash
git add backend/audits/test_notifications.py
git commit -m "test: add tests for Slack notification module"
```

---

### Task 5: Hook Notifications into `run_audit`

**Files:**
- Modify: `backend/audits/services.py:1,128-148`
- Modify: `backend/audits/test_services.py` (add one test)

**Step 1: Write a failing test**

Add to `backend/audits/test_services.py`, in the `RunAuditSuccessTests` class:

```python
@patch("audits.services.send_slack_notification")
@patch("audits.services.cleanup_scaffold")
@patch("audits.services.create_scaffold")
@patch("audits.services.subprocess.run")
@patch("audits.services.requests.get")
def test_sends_slack_notification_on_failure(
    self, mock_get, mock_subprocess, mock_create_scaffold, mock_cleanup, mock_slack
):
    """Slack notification fires when audit has failed rules."""
    mock_response = Mock()
    mock_response.text = self.config_text
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    scaffold_dir = Path(tempfile.mkdtemp(prefix="netaudit_test_"))
    mock_create_scaffold.return_value = scaffold_dir

    report_file = scaffold_dir / "report.json"
    report_file.write_text(json.dumps(self.mock_report))

    mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="")

    run_audit(self.device.id)

    mock_slack.assert_called_once()
    audit_run = mock_slack.call_args[0][0]
    self.assertEqual(audit_run.summary["failed"], 1)

    cleanup_scaffold(scaffold_dir)
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest backend/audits/test_services.py::RunAuditSuccessTests::test_sends_slack_notification_on_failure -v`
Expected: FAIL — `send_slack_notification` not imported/called yet

**Step 3: Wire up the notification call**

In `backend/audits/services.py`:

Add import at the top (after existing imports):

```python
from audits.notifications import send_slack_notification
```

After line 148 (the `audit_run.save(...)` in the finalize block), add:

```python
        # Send Slack notification if any rules failed
        if audit_run.summary.get("failed", 0) > 0:
            send_slack_notification(audit_run)
```

**Step 4: Run the test to verify it passes**

Run: `python -m pytest backend/audits/test_services.py::RunAuditSuccessTests::test_sends_slack_notification_on_failure -v`
Expected: PASS

**Step 5: Run full test suite to check for regressions**

Run: `python -m pytest backend/audits/test_services.py -v`
Expected: all tests PASS

**Step 6: Commit**

```bash
git add backend/audits/services.py backend/audits/test_services.py
git commit -m "feat: send Slack notification when audit has failures"
```

---

### Task 6: Add Test Slack Webhook API Endpoint

**Files:**
- Modify: `backend/settings/views.py`
- Modify: `backend/settings/urls.py`
- Modify: `backend/settings/tests.py`

**Step 1: Write failing tests**

Add to `backend/settings/tests.py`:

```python
from unittest.mock import patch, Mock


class TestSlackWebhookAPITests(APITestCase):

    def test_test_slack_requires_url(self):
        url = reverse("test-slack")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("settings.views.send_test_slack_notification")
    def test_test_slack_success(self, mock_send):
        mock_send.return_value = True
        url = reverse("test-slack")
        response = self.client.post(
            url,
            {"webhook_url": "https://hooks.slack.com/services/T00/B00/xxx"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

    @patch("settings.views.send_test_slack_notification")
    def test_test_slack_failure(self, mock_send):
        mock_send.return_value = False
        url = reverse("test-slack")
        response = self.client.post(
            url,
            {"webhook_url": "https://hooks.slack.com/services/T00/B00/xxx"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/settings/tests.py -v -k "test_slack"`
Expected: FAIL — no URL named `test-slack`

**Step 3: Add the view**

In `backend/settings/views.py`, add:

```python
from audits.notifications import send_test_slack_notification


@api_view(["POST"])
def test_slack_view(request):
    webhook_url = request.data.get("webhook_url", "").strip()
    if not webhook_url:
        return Response(
            {"error": "webhook_url is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    success = send_test_slack_notification(webhook_url)
    if success:
        return Response({"success": True})
    return Response(
        {"success": False, "error": "Failed to send test message"},
        status=status.HTTP_502_BAD_GATEWAY,
    )
```

**Step 4: Add the URL**

In `backend/settings/urls.py`, add:

```python
path("settings/test-slack/", views.test_slack_view, name="test-slack"),
```

**Step 5: Run tests to verify they pass**

Run: `python -m pytest backend/settings/tests.py -v -k "test_slack"`
Expected: all 3 new tests PASS

**Step 6: Commit**

```bash
git add backend/settings/views.py backend/settings/urls.py backend/settings/tests.py
git commit -m "feat: add test-slack API endpoint"
```

---

### Task 7: Update Frontend Types and Settings Hook

**Files:**
- Modify: `frontend/src/types/settings.ts`
- Modify: `frontend/src/hooks/use-settings.ts`

**Step 1: Update the SiteSettings type**

In `frontend/src/types/settings.ts`, change to:

```typescript
export interface SiteSettings {
  default_api_endpoint: string;
  slack_webhook_url: string;
}
```

**Step 2: Add the test-slack hook**

In `frontend/src/hooks/use-settings.ts`, add:

```typescript
export function useTestSlackWebhook() {
  return useMutation({
    mutationFn: async (webhookUrl: string) => {
      const response = await api.post("/settings/test-slack/", {
        webhook_url: webhookUrl,
      });
      return response.data;
    },
    onSuccess: () => toast.success("Test message sent to Slack"),
    onError: () => toast.error("Failed to send test message"),
  });
}
```

**Step 3: Commit**

```bash
git add frontend/src/types/settings.ts frontend/src/hooks/use-settings.ts
git commit -m "feat: add slack_webhook_url to frontend types and hooks"
```

---

### Task 8: Add Notifications Card to Settings Page

**Files:**
- Modify: `frontend/src/pages/settings.tsx`

**Step 1: Update the settings page**

In `frontend/src/pages/settings.tsx`:

Add imports:
```typescript
import { Send } from "lucide-react";
import { useTestSlackWebhook } from "@/hooks/use-settings";
```

Add state and hook inside `SettingsPage`:
```typescript
const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
const testSlack = useTestSlackWebhook();
```

Update the `useEffect` to also set `slackWebhookUrl`:
```typescript
useEffect(() => {
  if (settings) {
    setDefaultApiEndpoint(settings.default_api_endpoint);
    setSlackWebhookUrl(settings.slack_webhook_url);
  }
}, [settings]);
```

Update `handleSubmit` to include `slack_webhook_url`:
```typescript
await updateMutation.mutateAsync({
  default_api_endpoint: defaultApiEndpoint,
  slack_webhook_url: slackWebhookUrl,
});
```

Add a new Card after the Tags card:
```tsx
<Card>
  <CardHeader>
    <CardTitle>Notifications</CardTitle>
  </CardHeader>
  <CardContent className="space-y-4">
    <div className="space-y-2">
      <Label htmlFor="slack_webhook_url">Slack Webhook URL</Label>
      <div className="flex gap-2">
        <Input
          id="slack_webhook_url"
          type="url"
          placeholder="https://hooks.slack.com/services/..."
          value={slackWebhookUrl}
          onChange={(e) => setSlackWebhookUrl(e.target.value)}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!slackWebhookUrl.trim() || testSlack.isPending}
          onClick={() => testSlack.mutate(slackWebhookUrl)}
        >
          <Send className="h-4 w-4 mr-1" />
          Test
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">
        Receive a notification when an audit has failed rules.
        Paste an incoming webhook URL from your Slack workspace.
      </p>
    </div>
  </CardContent>
</Card>
```

Note: The Slack webhook URL is saved along with all other settings when the user clicks "Save". The "Test" button sends a test message using the current input value (even if unsaved).

**Step 2: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors

**Step 3: Commit**

```bash
git add frontend/src/pages/settings.tsx
git commit -m "feat: add Slack webhook configuration UI to settings page"
```

---

### Task 9: Run Full Test Suite and Final Verification

**Step 1: Run all backend tests**

Run: `python -m pytest backend/ -v`
Expected: all tests PASS

**Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: build succeeds

**Step 3: Final commit if any cleanup needed**

Only if adjustments were needed from the verification step.
