from django.core.exceptions import ValidationError
from django.db import models


class SimpleRule(models.Model):
    """A declarative rule that checks device config against a pattern."""

    class RuleType(models.TextChoices):
        MUST_CONTAIN = "must_contain", "Must Contain"
        MUST_NOT_CONTAIN = "must_not_contain", "Must Not Contain"
        REGEX_MATCH = "regex_match", "Regex Match"
        REGEX_NO_MATCH = "regex_no_match", "Regex No Match"

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFO = "info", "Info"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=30, choices=RuleType.choices)
    pattern = models.TextField(help_text="String literal or regex pattern")
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    enabled = models.BooleanField(default=True)
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="simple_rules",
        null=True,
        blank=True,
        help_text="If null, rule applies to all devices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class CustomRule(models.Model):
    """A user-supplied pytest file executed during an audit run."""

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFO = "info", "Info"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    filename = models.CharField(max_length=255, help_text="e.g. test_ntp.py")
    content = models.TextField(
        help_text="Python source code of the pytest test file",
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    enabled = models.BooleanField(default=True)
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="custom_rules",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if not self.filename.startswith("test_"):
            raise ValidationError(
                {"filename": "Filename must start with 'test_'."}
            )
        if not self.filename.endswith(".py"):
            raise ValidationError(
                {"filename": "Filename must end with '.py'."}
            )
