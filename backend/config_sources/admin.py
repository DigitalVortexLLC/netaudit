from django.contrib import admin

from .models import ConfigSource, NetmikoDeviceType, SshConfigSource


@admin.register(NetmikoDeviceType)
class NetmikoDeviceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "driver", "default_command", "extra_commands", "created_at"]
    search_fields = ["name", "driver"]


@admin.register(ConfigSource)
class ConfigSourceAdmin(admin.ModelAdmin):
    list_display = ["id", "source_type", "created_at", "updated_at"]
    list_filter = ["source_type"]


@admin.register(SshConfigSource)
class SshConfigSourceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "source_type",
        "netmiko_device_type",
        "hostname",
        "port",
        "username",
        "created_at",
    ]
    list_filter = ["netmiko_device_type"]
    search_fields = ["hostname", "username"]
