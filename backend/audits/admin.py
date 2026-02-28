from django.contrib import admin

from audits.models import AuditRun, AuditSchedule, RuleResult


class RuleResultInline(admin.TabularInline):
    model = RuleResult
    extra = 0
    readonly_fields = [
        "simple_rule",
        "custom_rule",
        "test_node_id",
        "outcome",
        "message",
        "duration",
        "severity",
    ]


@admin.register(AuditRun)
class AuditRunAdmin(admin.ModelAdmin):
    list_display = ["device", "status", "trigger", "created_at"]
    list_filter = ["status", "trigger", "created_at"]
    inlines = [RuleResultInline]


@admin.register(AuditSchedule)
class AuditScheduleAdmin(admin.ModelAdmin):
    list_display = ["name", "device", "cron_expression", "enabled", "created_at"]
    list_filter = ["enabled"]
