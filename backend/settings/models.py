from django.db import models


class SiteSettings(models.Model):
    default_api_endpoint = models.URLField(
        blank=True,
        default="",
        help_text="Base URL for devices without a custom endpoint. "
        "Effective URL: <this>/<device_name>",
    )

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
