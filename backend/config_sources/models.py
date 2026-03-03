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


class ConfigSource(models.Model):
    SOURCE_TYPES = [
        ("api", "API Endpoint"),
        ("git", "Git Repository"),
        ("manual", "Manual"),
        ("ssh", "SSH (Netmiko)"),
    ]

    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ConfigSource({self.source_type}, pk={self.pk})"


class SshConfigSource(ConfigSource):
    netmiko_device_type = models.ForeignKey(
        NetmikoDeviceType, on_delete=models.PROTECT
    )
    hostname = models.CharField(max_length=255, blank=True, default="")
    port = models.IntegerField(default=22)
    username = EncryptedCharField(max_length=255)
    password = EncryptedCharField(max_length=255, blank=True, default="")
    ssh_key = EncryptedTextField(blank=True, default="")
    command_override = models.CharField(max_length=500, blank=True, default="")
    prompt_overrides = models.JSONField(default=dict, blank=True)
    timeout = models.IntegerField(default=30)

    def __str__(self):
        target = self.hostname or "(device hostname)"
        return f"SSH: {self.username}@{target} via {self.netmiko_device_type.driver}"
