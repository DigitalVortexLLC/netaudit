from unittest.mock import Mock, patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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
