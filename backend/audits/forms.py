from django import forms

from .models import AuditSchedule


class AuditScheduleForm(forms.ModelForm):
    class Meta:
        model = AuditSchedule
        fields = ["name", "device", "cron_expression", "enabled"]
