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

    def test_str(self):
        settings = SiteSettings.load()
        self.assertEqual(str(settings), "Site Settings")


class SiteSettingsAPITests(APITestCase):

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
