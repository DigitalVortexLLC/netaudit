from unittest.mock import Mock, patch

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
