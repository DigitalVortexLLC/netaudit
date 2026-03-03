from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField


class NetmikoDeviceType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    driver = models.CharField(max_length=100)
    default_command = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
