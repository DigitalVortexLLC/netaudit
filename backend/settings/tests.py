from django.test import TestCase

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
