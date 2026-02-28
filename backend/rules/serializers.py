import ast

from rest_framework import serializers

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
        try:
            ast.parse(value)
        except SyntaxError as exc:
            raise serializers.ValidationError(
                f"Invalid Python syntax: {exc}"
            )
        return value
