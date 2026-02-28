from django.contrib import admin

from .models import Device, DeviceHeader


class DeviceHeaderInline(admin.TabularInline):
    model = DeviceHeader
    extra = 1


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "hostname", "api_endpoint", "enabled", "created_at"]
    search_fields = ["name", "hostname"]
    inlines = [DeviceHeaderInline]
