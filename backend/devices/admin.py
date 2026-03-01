from django.contrib import admin

from .models import Device, DeviceGroup, DeviceHeader


class DeviceHeaderInline(admin.TabularInline):
    model = DeviceHeader
    extra = 1


@admin.register(DeviceGroup)
class DeviceGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "hostname", "api_endpoint", "enabled", "created_at"]
    search_fields = ["name", "hostname"]
    inlines = [DeviceHeaderInline]
