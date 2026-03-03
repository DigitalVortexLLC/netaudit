from django.db import models


class SiteSettings(models.Model):
    default_api_endpoint = models.URLField(
        blank=True,
        default="",
        help_text="Base URL for devices without a custom endpoint. "
        "Effective URL: <this>/<device_name>",
    )
    slack_webhook_url = models.URLField(
        blank=True,
        default="",
        help_text="Slack incoming webhook URL for audit failure notifications.",
    )
    public_registration_enabled = models.BooleanField(
        default=True,
        help_text="Allow new users to register via the public signup page.",
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
