from django import forms

from .models import CustomRule, SimpleRule


class SimpleRuleForm(forms.ModelForm):
    class Meta:
        model = SimpleRule
        fields = [
            "name",
            "description",
            "rule_type",
            "pattern",
            "severity",
            "enabled",
            "device",
            "group",
        ]


class CustomRuleForm(forms.ModelForm):
    class Meta:
        model = CustomRule
        fields = [
            "name",
            "description",
            "filename",
            "content",
            "severity",
            "enabled",
            "device",
            "group",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"class": "code-textarea"}),
        }
