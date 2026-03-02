from rest_framework import serializers

from .ast_validator import validate_custom_rule_ast
from .models import CustomRule, SimpleRule


class SimpleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimpleRule
        fields = "__all__"


class CustomRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomRule
        fields = "__all__"

    def validate_filename(self, value):
        if not value.startswith("test_"):
            raise serializers.ValidationError(
                "Filename must start with 'test_'."
            )
        if not value.endswith(".py"):
            raise serializers.ValidationError(
                "Filename must end with '.py'."
            )
        return value

    def validate_content(self, value):
        errors = validate_custom_rule_ast(value)
        if errors:
            messages = [
                f"Line {e['line']}: {e['message']}" for e in errors
            ]
            raise serializers.ValidationError(messages)

        return value
