# Webhook Notifications Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a webhook notification system that fires HTTP POST requests with device and rule failure details when audit rules fail, enabling external remediation systems.

**Architecture:** New `notifications` Django app with `WebhookProvider` + `WebhookHeader` models (mirroring `Device`/`DeviceHeader`). A `dispatch_webhooks()` function is called at the end of `run_audit()`. Frontend adds a "Webhooks" card to the Settings page. Configurable trigger mode: per-audit or per-rule.

**Tech Stack:** Django, DRF (ViewSet + nested serializer), React + TanStack Query + shadcn/ui

**Design doc:** `docs/plans/2026-03-02-webhook-notifications-design.md`

---

### Task 1: Create notifications Django app scaffold

**Files:**
- Create: `backend/notifications/__init__.py`
- Create: `backend/notifications/apps.py`
- Create: `backend/notifications/admin.py`
- Create: `backend/notifications/models.py`
- Modify: `backend/config/settings/base.py:39` (add to INSTALLED_APPS)

**Step 1: Create the app directory and files**

Create `backend/notifications/__init__.py` (empty).

Create `backend/notifications/apps.py`:
```python
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
```

Create `backend/notifications/admin.py`:
```python
from django.contrib import admin

from .models import WebhookHeader, WebhookProvider


class WebhookHeaderInline(admin.TabularInline):
    model = WebhookHeader
    extra = 1


@admin.register(WebhookProvider)
class WebhookProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "url", "enabled", "trigger_mode"]
    list_filter = ["enabled", "trigger_mode"]
    inlines = [WebhookHeaderInline]
```

Create `backend/notifications/models.py`:
```python
from django.db import models


class WebhookProvider(models.Model):
    class TriggerMode(models.TextChoices):
        PER_AUDIT = "per_audit", "Per Audit"
        PER_RULE = "per_rule", "Per Rule"

    name = models.CharField(max_length=255)
    url = models.URLField()
    enabled = models.BooleanField(default=True)
    trigger_mode = models.CharField(
        max_length=20,
        choices=TriggerMode.choices,
        default=TriggerMode.PER_AUDIT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WebhookHeader(models.Model):
    provider = models.ForeignKey(
        WebhookProvider,
        on_delete=models.CASCADE,
        related_name="headers",
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=1024)

    class Meta:
        unique_together = [("provider", "key")]

    def __str__(self):
        return f"{self.key}: {self.value}"
```

**Step 2: Register in INSTALLED_APPS**

In `backend/config/settings/base.py`, add `"notifications"` to the `INSTALLED_APPS` list after `"settings"`:
```python
    # Local apps
    "accounts",
    "devices",
    "rules",
    "audits",
    "common",
    "settings",
    "notifications",
```

**Step 3: Create and run migration**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/nifty-banach/backend
python manage.py makemigrations notifications
python manage.py migrate
```

**Step 4: Commit**

```bash
git add backend/notifications/ backend/config/settings/base.py
git commit -m "feat: add notifications app with WebhookProvider and WebhookHeader models"
```

---

### Task 2: Write model tests

**Files:**
- Create: `backend/notifications/tests.py`

**Step 1: Write model tests**

Create `backend/notifications/tests.py`:
```python
from django.db import IntegrityError
from django.test import TestCase

from .models import WebhookHeader, WebhookProvider


class WebhookProviderModelTests(TestCase):

    def test_create_webhook_provider(self):
        provider = WebhookProvider.objects.create(
            name="Remediation API",
            url="https://remediation.example.com/webhook",
        )
        self.assertEqual(provider.name, "Remediation API")
        self.assertEqual(provider.url, "https://remediation.example.com/webhook")
        self.assertTrue(provider.enabled)
        self.assertEqual(provider.trigger_mode, "per_audit")
        self.assertIsNotNone(provider.created_at)
        self.assertIsNotNone(provider.updated_at)

    def test_trigger_mode_choices(self):
        provider = WebhookProvider.objects.create(
            name="Per Rule Hook",
            url="https://example.com/hook",
            trigger_mode="per_rule",
        )
        self.assertEqual(provider.trigger_mode, "per_rule")

    def test_str(self):
        provider = WebhookProvider.objects.create(
            name="My Webhook",
            url="https://example.com/hook",
        )
        self.assertEqual(str(provider), "My Webhook")

    def test_ordering(self):
        WebhookProvider.objects.create(name="Zebra", url="https://z.com/hook")
        WebhookProvider.objects.create(name="Alpha", url="https://a.com/hook")
        names = list(WebhookProvider.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Zebra"])

    def test_disabled_provider(self):
        provider = WebhookProvider.objects.create(
            name="Disabled",
            url="https://example.com/hook",
            enabled=False,
        )
        self.assertFalse(provider.enabled)


class WebhookHeaderModelTests(TestCase):

    def setUp(self):
        self.provider = WebhookProvider.objects.create(
            name="Test Provider",
            url="https://example.com/hook",
        )

    def test_create_header(self):
        header = WebhookHeader.objects.create(
            provider=self.provider,
            key="Authorization",
            value="Bearer token123",
        )
        self.assertEqual(header.provider, self.provider)
        self.assertEqual(header.key, "Authorization")
        self.assertEqual(header.value, "Bearer token123")

    def test_str(self):
        header = WebhookHeader.objects.create(
            provider=self.provider,
            key="X-API-Key",
            value="abc123",
        )
        self.assertEqual(str(header), "X-API-Key: abc123")

    def test_unique_together(self):
        WebhookHeader.objects.create(
            provider=self.provider, key="X-Custom", value="v1",
        )
        with self.assertRaises(IntegrityError):
            WebhookHeader.objects.create(
                provider=self.provider, key="X-Custom", value="v2",
            )

    def test_cascade_delete(self):
        WebhookHeader.objects.create(
            provider=self.provider, key="Auth", value="token",
        )
        self.assertEqual(WebhookHeader.objects.count(), 1)
        self.provider.delete()
        self.assertEqual(WebhookHeader.objects.count(), 0)

    def test_related_name(self):
        WebhookHeader.objects.create(
            provider=self.provider, key="X-Api-Key", value="key123",
        )
        headers = self.provider.headers.all()
        self.assertEqual(headers.count(), 1)
        self.assertEqual(headers.first().key, "X-Api-Key")
```

**Step 2: Run tests to verify they pass**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/nifty-banach/backend
python manage.py test notifications -v2
```

Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/notifications/tests.py
git commit -m "test: add model tests for WebhookProvider and WebhookHeader"
```

---

### Task 3: Create DRF serializer and ViewSet

**Files:**
- Create: `backend/notifications/serializers.py`
- Create: `backend/notifications/views.py`
- Create: `backend/notifications/urls.py`
- Modify: `backend/config/urls.py:14` (add URL include)

**Step 1: Create serializer**

Create `backend/notifications/serializers.py`. Mirror the `DeviceSerializer` pattern with nested headers:
```python
from rest_framework import serializers

from .models import WebhookHeader, WebhookProvider


class WebhookHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookHeader
        fields = ["id", "key", "value"]


class WebhookProviderSerializer(serializers.ModelSerializer):
    headers = WebhookHeaderSerializer(many=True, required=False)

    class Meta:
        model = WebhookProvider
        fields = [
            "id",
            "name",
            "url",
            "enabled",
            "trigger_mode",
            "headers",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        headers_data = validated_data.pop("headers", [])
        provider = WebhookProvider.objects.create(**validated_data)
        for header_data in headers_data:
            WebhookHeader.objects.create(provider=provider, **header_data)
        return provider

    def update(self, instance, validated_data):
        headers_data = validated_data.pop("headers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if headers_data is not None:
            instance.headers.all().delete()
            for header_data in headers_data:
                WebhookHeader.objects.create(provider=instance, **header_data)

        return instance
```

**Step 2: Create ViewSet**

Create `backend/notifications/views.py`:
```python
import logging
from datetime import datetime, timezone

import requests as http_requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import WebhookProvider
from .serializers import WebhookProviderSerializer

logger = logging.getLogger(__name__)


class WebhookProviderViewSet(viewsets.ModelViewSet):
    queryset = WebhookProvider.objects.prefetch_related("headers").all()
    serializer_class = WebhookProviderSerializer
    search_fields = ["name", "url"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        provider = self.get_object()
        headers = {h.key: h.value for h in provider.headers.all()}
        headers["Content-Type"] = "application/json"

        payload = {
            "event": "webhook.test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "This is a test webhook from NetAudit.",
            "provider_name": provider.name,
        }

        try:
            response = http_requests.post(
                provider.url, json=payload, headers=headers, timeout=10,
            )
            return Response({
                "success": True,
                "status_code": response.status_code,
            })
        except http_requests.RequestException as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
```

**Step 3: Create URL routing**

Create `backend/notifications/urls.py`:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WebhookProviderViewSet

router = DefaultRouter()
router.register("webhooks", WebhookProviderViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
```

**Step 4: Register URLs in main config**

In `backend/config/urls.py`, add after line 14 (`path("api/v1/", include("settings.urls")),`):
```python
    path("api/v1/notifications/", include("notifications.urls")),
```

**Step 5: Commit**

```bash
git add backend/notifications/serializers.py backend/notifications/views.py backend/notifications/urls.py backend/config/urls.py
git commit -m "feat: add webhook provider REST API with nested headers and test action"
```

---

### Task 4: Write API tests

**Files:**
- Modify: `backend/notifications/tests.py` (append API tests)

**Step 1: Add API tests**

Append to `backend/notifications/tests.py`:
```python
from unittest.mock import Mock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class WebhookProviderAPITests(APITestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.client.force_authenticate(user=self.user)

        self.provider = WebhookProvider.objects.create(
            name="Test Webhook",
            url="https://example.com/webhook",
            trigger_mode="per_audit",
        )
        WebhookHeader.objects.create(
            provider=self.provider, key="Authorization", value="Bearer test-token",
        )
        self.list_url = reverse("webhookprovider-list")
        self.detail_url = reverse("webhookprovider-detail", kwargs={"pk": self.provider.pk})

    def test_list_providers(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Test Webhook")

    def test_list_providers_includes_headers(self):
        response = self.client.get(self.list_url)
        headers = response.data["results"][0]["headers"]
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0]["key"], "Authorization")

    def test_create_provider(self):
        data = {
            "name": "New Webhook",
            "url": "https://new.example.com/hook",
            "trigger_mode": "per_rule",
            "headers": [
                {"key": "X-API-Key", "value": "secret123"},
            ],
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Webhook")
        self.assertEqual(response.data["trigger_mode"], "per_rule")
        self.assertEqual(len(response.data["headers"]), 1)

    def test_create_provider_without_headers(self):
        data = {
            "name": "No Headers",
            "url": "https://example.com/hook",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["headers"]), 0)

    def test_create_provider_invalid_url(self):
        data = {"name": "Bad URL", "url": "not-a-url"}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_provider(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Webhook")
        self.assertEqual(len(response.data["headers"]), 1)

    def test_update_provider(self):
        data = {
            "name": "Updated",
            "url": "https://updated.example.com/hook",
            "trigger_mode": "per_rule",
            "headers": [],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.name, "Updated")
        self.assertEqual(self.provider.trigger_mode, "per_rule")
        self.assertEqual(self.provider.headers.count(), 0)

    def test_partial_update_replaces_headers(self):
        data = {
            "headers": [{"key": "X-New", "value": "new-value"}],
        }
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.provider.headers.count(), 1)
        self.assertEqual(self.provider.headers.first().key, "X-New")

    def test_partial_update_without_headers_preserves_them(self):
        data = {"name": "Renamed"}
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.provider.headers.count(), 1)
        self.assertEqual(self.provider.headers.first().key, "Authorization")

    def test_delete_provider(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WebhookProvider.objects.filter(pk=self.provider.pk).exists())

    def test_delete_provider_removes_headers(self):
        self.client.delete(self.detail_url)
        self.assertEqual(WebhookHeader.objects.count(), 0)

    @patch("notifications.views.http_requests.post")
    def test_test_action_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        url = reverse("webhookprovider-test", kwargs={"pk": self.provider.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status_code"], 200)

        called_headers = mock_post.call_args[1]["headers"]
        self.assertEqual(called_headers["Authorization"], "Bearer test-token")
        self.assertEqual(called_headers["Content-Type"], "application/json")

    @patch("notifications.views.http_requests.post")
    def test_test_action_failure(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")

        url = reverse("webhookprovider-test", kwargs={"pk": self.provider.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(response.data["success"])
```

**Step 2: Run tests**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/nifty-banach/backend
python manage.py test notifications -v2
```

Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/notifications/tests.py
git commit -m "test: add API tests for webhook provider CRUD and test action"
```

---

### Task 5: Implement webhook dispatch service

**Files:**
- Create: `backend/notifications/dispatch.py`
- Modify: `backend/audits/services.py:128` (call dispatch after parse_results)

**Step 1: Create dispatch module**

Create `backend/notifications/dispatch.py`:
```python
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
```

**Step 2: Integrate into audit service**

In `backend/audits/services.py`, add the import at the top (after existing imports around line 22):
```python
from notifications.dispatch import dispatch_webhooks
```

Then after line 148 (after `audit_run.save(update_fields=[...])` in the finalization section), add:
```python

        # ----------------------------------------------------------
        # 6. Dispatch webhook notifications
        # ----------------------------------------------------------
        dispatch_webhooks(audit_run)
```

**Step 3: Commit**

```bash
git add backend/notifications/dispatch.py backend/audits/services.py
git commit -m "feat: add webhook dispatch service and integrate into audit runner"
```

---

### Task 6: Write dispatch tests

**Files:**
- Create: `backend/notifications/test_dispatch.py`

**Step 1: Write dispatch tests**

Create `backend/notifications/test_dispatch.py`:
```python
from unittest.mock import Mock, patch, call

from django.test import TestCase

from audits.models import AuditRun, RuleResult
from devices.models import Device, DeviceGroup
from notifications.dispatch import dispatch_webhooks
from notifications.models import WebhookHeader, WebhookProvider
from rules.models import SimpleRule


class DispatchWebhooksTests(TestCase):

    def setUp(self):
        self.device = Device.objects.create(
            name="switch-01", hostname="10.0.1.1",
            api_endpoint="https://switch-01.local/api",
        )
        self.group = DeviceGroup.objects.create(name="datacenter-a")
        self.device.groups.add(self.group)

        self.audit_run = AuditRun.objects.create(
            device=self.device,
            status="completed",
            summary={"total": 3, "passed": 1, "failed": 2, "error": 0},
        )

        self.rule = SimpleRule.objects.create(
            name="NTP required",
            rule_type="must_contain",
            pattern="ntp server",
            severity="high",
        )
        RuleResult.objects.create(
            audit_run=self.audit_run,
            simple_rule=self.rule,
            test_node_id="test_simple_rules.py::test_simple_rule[rule-1-ntp]",
            outcome="failed",
            message="Pattern 'ntp server' not found",
            severity="high",
        )
        RuleResult.objects.create(
            audit_run=self.audit_run,
            test_node_id="test_simple_rules.py::test_simple_rule[rule-2-dns]",
            outcome="passed",
            message="",
            severity="medium",
        )

    @patch("notifications.dispatch.requests.post")
    def test_per_audit_sends_single_request(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        WebhookProvider.objects.create(
            name="Hook", url="https://hook.example.com/api",
            trigger_mode="per_audit",
        )

        dispatch_webhooks(self.audit_run)

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["event"], "audit.completed")
        self.assertEqual(payload["device"]["name"], "switch-01")
        self.assertEqual(payload["device"]["hostname"], "10.0.1.1")
        self.assertEqual(payload["device"]["groups"], ["datacenter-a"])
        self.assertEqual(len(payload["failed_rules"]), 1)
        self.assertEqual(payload["failed_rules"][0]["rule_name"], "NTP required")
        self.assertEqual(payload["failed_rules"][0]["severity"], "high")

    @patch("notifications.dispatch.requests.post")
    def test_per_rule_sends_request_per_failure(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        # Add a second failure
        RuleResult.objects.create(
            audit_run=self.audit_run,
            test_node_id="test_simple_rules.py::test_simple_rule[rule-3-syslog]",
            outcome="failed",
            message="syslog not configured",
            severity="critical",
        )
        WebhookProvider.objects.create(
            name="Hook", url="https://hook.example.com/api",
            trigger_mode="per_rule",
        )

        dispatch_webhooks(self.audit_run)

        self.assertEqual(mock_post.call_count, 2)
        events = [c[1]["json"]["event"] for c in mock_post.call_args_list]
        self.assertTrue(all(e == "rule.failed" for e in events))

    @patch("notifications.dispatch.requests.post")
    def test_disabled_provider_not_called(self, mock_post):
        WebhookProvider.objects.create(
            name="Disabled", url="https://example.com/hook",
            enabled=False,
        )

        dispatch_webhooks(self.audit_run)

        mock_post.assert_not_called()

    @patch("notifications.dispatch.requests.post")
    def test_no_failures_skips_dispatch(self, mock_post):
        # Remove all failed results
        RuleResult.objects.filter(outcome="failed").delete()
        WebhookProvider.objects.create(
            name="Hook", url="https://example.com/hook",
        )

        dispatch_webhooks(self.audit_run)

        mock_post.assert_not_called()

    @patch("notifications.dispatch.requests.post")
    def test_sends_custom_headers(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        provider = WebhookProvider.objects.create(
            name="Hook", url="https://example.com/hook",
        )
        WebhookHeader.objects.create(
            provider=provider, key="Authorization", value="Bearer secret",
        )

        dispatch_webhooks(self.audit_run)

        called_headers = mock_post.call_args[1]["headers"]
        self.assertEqual(called_headers["Authorization"], "Bearer secret")
        self.assertEqual(called_headers["Content-Type"], "application/json")

    @patch("notifications.dispatch.requests.post")
    def test_request_failure_does_not_raise(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")
        WebhookProvider.objects.create(
            name="Hook", url="https://example.com/hook",
        )

        # Should not raise
        dispatch_webhooks(self.audit_run)

    @patch("notifications.dispatch.requests.post")
    def test_multiple_providers(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        WebhookProvider.objects.create(
            name="Hook 1", url="https://hook1.example.com/api",
            trigger_mode="per_audit",
        )
        WebhookProvider.objects.create(
            name="Hook 2", url="https://hook2.example.com/api",
            trigger_mode="per_audit",
        )

        dispatch_webhooks(self.audit_run)

        self.assertEqual(mock_post.call_count, 2)

    @patch("notifications.dispatch.requests.post")
    def test_no_providers_is_noop(self, mock_post):
        dispatch_webhooks(self.audit_run)
        mock_post.assert_not_called()
```

**Step 2: Run tests**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/nifty-banach/backend
python manage.py test notifications -v2
```

Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/notifications/test_dispatch.py
git commit -m "test: add dispatch_webhooks tests covering all trigger modes and edge cases"
```

---

### Task 7: Add frontend types and API hooks

**Files:**
- Create: `frontend/src/types/webhook.ts`
- Modify: `frontend/src/types/index.ts` (add export)
- Create: `frontend/src/hooks/use-webhooks.ts`

**Step 1: Create TypeScript types**

Create `frontend/src/types/webhook.ts`:
```typescript
export interface WebhookHeader {
  id?: number;
  key: string;
  value: string;
}

export interface WebhookProvider {
  id: number;
  name: string;
  url: string;
  enabled: boolean;
  trigger_mode: "per_audit" | "per_rule";
  headers: WebhookHeader[];
  created_at: string;
  updated_at: string;
}

export interface WebhookProviderFormData {
  name: string;
  url: string;
  enabled: boolean;
  trigger_mode: "per_audit" | "per_rule";
  headers: WebhookHeader[];
}

export interface WebhookTestResult {
  success: boolean;
  status_code?: number;
  error?: string;
}
```

**Step 2: Export from types index**

In `frontend/src/types/index.ts`, add:
```typescript
export * from "./webhook";
```

**Step 3: Create React Query hooks**

Create `frontend/src/hooks/use-webhooks.ts`:
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type {
  WebhookProvider,
  WebhookProviderFormData,
  WebhookTestResult,
  PaginatedResponse,
} from "@/types";

export function useWebhooks() {
  return useQuery({
    queryKey: ["webhooks"],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<WebhookProvider>>(
        "/notifications/webhooks/"
      );
      return response.data;
    },
  });
}

export function useWebhook(id: number) {
  return useQuery({
    queryKey: ["webhooks", id],
    queryFn: async () => {
      const response = await api.get<WebhookProvider>(
        `/notifications/webhooks/${id}/`
      );
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: WebhookProviderFormData) => {
      const response = await api.post<WebhookProvider>(
        "/notifications/webhooks/",
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      toast.success("Webhook created");
    },
    onError: () => toast.error("Failed to create webhook"),
  });
}

export function useUpdateWebhook(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: WebhookProviderFormData) => {
      const response = await api.put<WebhookProvider>(
        `/notifications/webhooks/${id}/`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      toast.success("Webhook updated");
    },
    onError: () => toast.error("Failed to update webhook"),
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/notifications/webhooks/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      toast.success("Webhook deleted");
    },
    onError: () => toast.error("Failed to delete webhook"),
  });
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<WebhookTestResult>(
        `/notifications/webhooks/${id}/test/`
      );
      return response.data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(`Test successful (status ${data.status_code})`);
      } else {
        toast.error(`Test failed: ${data.error}`);
      }
    },
    onError: () => toast.error("Test request failed"),
  });
}
```

**Step 4: Commit**

```bash
git add frontend/src/types/webhook.ts frontend/src/types/index.ts frontend/src/hooks/use-webhooks.ts
git commit -m "feat: add frontend types and React Query hooks for webhooks"
```

---

### Task 8: Add Webhooks UI to Settings page

**Files:**
- Modify: `frontend/src/pages/settings.tsx`

**Step 1: Add Webhooks card to Settings page**

Replace the contents of `frontend/src/pages/settings.tsx` with the existing content plus a new Webhooks card. The card shows a table of providers with add/edit/delete/test actions, and a dialog form for creating/editing.

Read the current file and add the following after the Tags card:

Import the additional dependencies at the top:
```typescript
import { useState, useEffect } from "react";
import { Plus, Save, Pencil, Trash2, Zap, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSiteSettings, useUpdateSiteSettings } from "@/hooks/use-settings";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/use-tags";
import {
  useWebhooks,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
} from "@/hooks/use-webhooks";
import { TagBadge } from "@/components/tag-badge";
import { DeleteDialog } from "@/components/delete-dialog";
import type { WebhookProvider, WebhookHeader, WebhookProviderFormData } from "@/types";
```

Add a `WebhookFormDialog` component (inside the file, before the `SettingsPage` export):
```typescript
function WebhookFormDialog({
  webhook,
  open,
  onOpenChange,
}: {
  webhook?: WebhookProvider;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createMutation = useCreateWebhook();
  const updateMutation = useUpdateWebhook(webhook?.id ?? 0);
  const isEdit = !!webhook;

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [triggerMode, setTriggerMode] = useState<"per_audit" | "per_rule">("per_audit");
  const [headers, setHeaders] = useState<WebhookHeader[]>([]);

  useEffect(() => {
    if (webhook) {
      setName(webhook.name);
      setUrl(webhook.url);
      setEnabled(webhook.enabled);
      setTriggerMode(webhook.trigger_mode);
      setHeaders(webhook.headers.map((h) => ({ key: h.key, value: h.value })));
    } else {
      setName("");
      setUrl("");
      setEnabled(true);
      setTriggerMode("per_audit");
      setHeaders([]);
    }
  }, [webhook, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const data: WebhookProviderFormData = {
      name,
      url,
      enabled,
      trigger_mode: triggerMode,
      headers,
    };
    if (isEdit) {
      await updateMutation.mutateAsync(data);
    } else {
      await createMutation.mutateAsync(data);
    }
    onOpenChange(false);
  };

  const addHeader = () => setHeaders([...headers, { key: "", value: "" }]);
  const removeHeader = (index: number) =>
    setHeaders(headers.filter((_, i) => i !== index));
  const updateHeader = (index: number, field: "key" | "value", val: string) =>
    setHeaders(headers.map((h, i) => (i === index ? { ...h, [field]: val } : h)));

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Webhook" : "Add Webhook"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhook-name">Name</Label>
            <Input
              id="webhook-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Remediation API"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="webhook-url">URL</Label>
            <Input
              id="webhook-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/webhook"
              required
            />
          </div>
          <div className="flex items-center gap-4">
            <div className="space-y-2 flex-1">
              <Label>Trigger Mode</Label>
              <Select value={triggerMode} onValueChange={(v) => setTriggerMode(v as "per_audit" | "per_rule")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="per_audit">Per Audit</SelectItem>
                  <SelectItem value="per_rule">Per Rule</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 pt-6">
              <Switch checked={enabled} onCheckedChange={setEnabled} />
              <Label>Enabled</Label>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Headers</Label>
              <Button type="button" variant="outline" size="sm" onClick={addHeader}>
                <Plus className="h-3 w-3 mr-1" />
                Add Header
              </Button>
            </div>
            {headers.map((header, i) => (
              <div key={i} className="flex gap-2">
                <Input
                  placeholder="Header name"
                  value={header.key}
                  onChange={(e) => updateHeader(i, "key", e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="Header value"
                  value={header.value}
                  onChange={(e) => updateHeader(i, "value", e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeHeader(i)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {isEdit ? "Update" : "Create"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

Add a `WebhooksCard` component:
```typescript
function WebhooksCard() {
  const { data: webhooksData } = useWebhooks();
  const deleteMutation = useDeleteWebhook();
  const testMutation = useTestWebhook();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookProvider | undefined>();

  const webhooks = webhooksData?.results ?? [];

  const handleEdit = (webhook: WebhookProvider) => {
    setEditingWebhook(webhook);
    setDialogOpen(true);
  };

  const handleAdd = () => {
    setEditingWebhook(undefined);
    setDialogOpen(true);
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Webhooks</CardTitle>
          <Button size="sm" onClick={handleAdd}>
            <Plus className="h-4 w-4" />
            Add Webhook
          </Button>
        </CardHeader>
        <CardContent>
          {webhooks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No webhooks configured. Add a webhook to receive notifications when audit rules fail.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {webhooks.map((webhook) => (
                  <TableRow key={webhook.id}>
                    <TableCell className="font-medium">{webhook.name}</TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                      {webhook.url}
                    </TableCell>
                    <TableCell className="text-sm">
                      {webhook.trigger_mode === "per_audit" ? "Per Audit" : "Per Rule"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${
                          webhook.enabled ? "bg-green-500" : "bg-gray-300"
                        }`}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => testMutation.mutate(webhook.id)}
                          disabled={testMutation.isPending}
                          title="Test webhook"
                        >
                          <Zap className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(webhook)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <DeleteDialog
                          name={webhook.name}
                          onConfirm={() => deleteMutation.mutate(webhook.id)}
                          loading={deleteMutation.isPending}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <WebhookFormDialog
        webhook={editingWebhook}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </>
  );
}
```

Then in the `SettingsPage` component's return, add `<WebhooksCard />` after the Tags card (before the closing `</div>`).

**Step 2: Verify the page renders**

Start the frontend dev server and navigate to `/settings`. Verify:
- The Webhooks card appears
- "No webhooks configured" message shows
- "Add Webhook" button opens the dialog
- Dialog has all fields: name, URL, trigger mode, enabled, headers

**Step 3: Commit**

```bash
git add frontend/src/pages/settings.tsx
git commit -m "feat: add webhooks management UI to settings page"
```

---

### Task 9: Run full test suite and verify

**Files:** None (verification only)

**Step 1: Run all backend tests**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/nifty-banach/backend
python manage.py test -v2
```

Expected: All tests pass, including new notifications tests.

**Step 2: Verify frontend builds**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/nifty-banach/frontend
npm run build
```

Expected: Build completes with no errors.

**Step 3: Commit (if any fixes were needed)**

If fixes were applied, commit them with an appropriate message.
