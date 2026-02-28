from django.db import models


class DeviceGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Device(models.Model):
    name = models.CharField(max_length=255, unique=True)
    hostname = models.CharField(max_length=255)
    api_endpoint = models.URLField(blank=True, default="")
    enabled = models.BooleanField(default=True)
    groups = models.ManyToManyField(
        "DeviceGroup",
        related_name="devices",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def effective_api_endpoint(self):
        if self.api_endpoint:
            return self.api_endpoint
        from settings.models import SiteSettings
        site = SiteSettings.load()
        if site.default_api_endpoint:
            base = site.default_api_endpoint.rstrip("/")
            return f"{base}/{self.name}"
        return ""


class DeviceHeader(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="headers",
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=1024)

    class Meta:
        unique_together = [("device", "key")]

    def __str__(self):
        return f"{self.key}: {self.value}"
