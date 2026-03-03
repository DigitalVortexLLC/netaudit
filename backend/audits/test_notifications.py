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
