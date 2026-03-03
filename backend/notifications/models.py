from django.db import models


class WebhookProvider(models.Model):
    class TriggerMode(models.TextChoices):
        PER_AUDIT = "per_audit", "Per Audit"
        PER_RULE = "per_rule", "Per Rule"

    name = models.CharField(max_length=255)
    url = models.URLField()
    enabled = models.BooleanField(default=True)
    trigger_mode = models.CharField(
        max_length=20,
        choices=TriggerMode.choices,
        default=TriggerMode.PER_AUDIT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WebhookHeader(models.Model):
    provider = models.ForeignKey(
        WebhookProvider,
        on_delete=models.CASCADE,
        related_name="headers",
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=1024)

    class Meta:
        unique_together = [("provider", "key")]

    def __str__(self):
        return f"{self.key}: {self.value}"
