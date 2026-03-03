from django.contrib import admin

from .models import NetmikoDeviceType


@admin.register(NetmikoDeviceType)
class NetmikoDeviceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "driver", "default_command", "created_at"]
    search_fields = ["name", "driver"]
