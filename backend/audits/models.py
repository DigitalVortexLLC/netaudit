from django.db import models


class AuditRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        FETCHING_CONFIG = "fetching_config", "Fetching Config"
        RUNNING_RULES = "running_rules", "Running Rules"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULED = "scheduled", "Scheduled"

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="audit_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    trigger = models.CharField(
        max_length=10,
        choices=Trigger.choices,
        default=Trigger.MANUAL,
    )
    config_snapshot = models.TextField(blank=True)
    config_fetched_at = models.DateTimeField(null=True, blank=True)
    pytest_json_report = models.JSONField(null=True, blank=True)
    summary = models.JSONField(
        null=True,
        blank=True,
        help_text="e.g. {passed: 5, failed: 2, error: 0}",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AuditRun {self.pk} - {self.device} ({self.status})"


class RuleResult(models.Model):
    class Outcome(models.TextChoices):
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        ERROR = "error", "Error"
        SKIPPED = "skipped", "Skipped"

    audit_run = models.ForeignKey(
        AuditRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    simple_rule = models.ForeignKey(
        "rules.SimpleRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    custom_rule = models.ForeignKey(
        "rules.CustomRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    test_node_id = models.CharField(max_length=500)
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    message = models.TextField(blank=True)
    duration = models.FloatField(null=True, blank=True)
    severity = models.CharField(max_length=10, default="medium")

    class Meta:
        ordering = ["test_node_id"]

    def __str__(self):
        return f"{self.test_node_id} - {self.outcome}"


class AuditSchedule(models.Model):
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    name = models.CharField(max_length=255)
    cron_expression = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    django_q_schedule_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.device})"
