from django.contrib import admin

from .models import CustomRule, SimpleRule


@admin.register(SimpleRule)
class SimpleRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "rule_type", "severity", "enabled", "device", "created_at"]
    list_filter = ["rule_type", "severity", "enabled"]
    search_fields = ["name", "description", "pattern"]


@admin.register(CustomRule)
class CustomRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "filename", "severity", "enabled", "device", "created_at"]
    list_filter = ["severity", "enabled"]
    search_fields = ["name", "description", "filename"]
