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
