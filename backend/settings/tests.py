from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import SiteSettings


class SiteSettingsModelTests(TestCase):

    def test_load_creates_singleton(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        settings = SiteSettings.load()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(settings.pk, 1)

    def test_load_returns_existing(self):
        SiteSettings.objects.create(
            pk=1, default_api_endpoint="https://example.com/api"
        )
        settings = SiteSettings.load()
        self.assertEqual(settings.default_api_endpoint, "https://example.com/api")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_save_forces_pk_1(self):
        settings = SiteSettings(pk=99, default_api_endpoint="https://test.com")
        settings.save()
        self.assertEqual(settings.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_default_api_endpoint_blank_by_default(self):
        settings = SiteSettings.load()
        self.assertEqual(settings.default_api_endpoint, "")

    def test_slack_webhook_url_blank_by_default(self):
        settings = SiteSettings.load()
        self.assertEqual(settings.slack_webhook_url, "")

    def test_str(self):
        settings = SiteSettings.load()
        self.assertEqual(str(settings), "Site Settings")


class SiteSettingsAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.user)

    def test_get_settings(self):
        url = reverse("site-settings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "")

    def test_put_settings(self):
        url = reverse("site-settings")
        response = self.client.put(
            url, {"default_api_endpoint": "https://new.example.com/api"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "https://new.example.com/api")

    def test_patch_settings(self):
        url = reverse("site-settings")
        response = self.client.patch(
            url, {"default_api_endpoint": "https://patched.example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "https://patched.example.com")

    def test_put_invalid_url(self):
        url = reverse("site-settings")
        response = self.client.put(
            url, {"default_api_endpoint": "not-a-url"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_blank_clears_default(self):
        site = SiteSettings.load()
        site.default_api_endpoint = "https://old.example.com"
        site.save()

        url = reverse("site-settings")
        response = self.client.put(
            url, {"default_api_endpoint": ""}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "")

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


class TestSlackWebhookAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.user)

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
