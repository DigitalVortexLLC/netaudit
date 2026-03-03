from django.contrib import admin

from .models import WebhookHeader, WebhookProvider


class WebhookHeaderInline(admin.TabularInline):
    model = WebhookHeader
    extra = 1


@admin.register(WebhookProvider)
class WebhookProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "url", "enabled", "trigger_mode"]
    list_filter = ["enabled", "trigger_mode"]
    inlines = [WebhookHeaderInline]
