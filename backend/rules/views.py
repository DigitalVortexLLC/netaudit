import ast

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import CustomRule, SimpleRule
from .serializers import CustomRuleSerializer, SimpleRuleSerializer


class SimpleRuleViewSet(viewsets.ModelViewSet):
    queryset = SimpleRule.objects.all()
    serializer_class = SimpleRuleSerializer
    filterset_fields = ["device", "group", "enabled", "severity", "rule_type"]
    search_fields = ["name", "description", "pattern"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]


class CustomRuleViewSet(viewsets.ModelViewSet):
    queryset = CustomRule.objects.all()
    serializer_class = CustomRuleSerializer
    filterset_fields = ["device", "group", "enabled", "severity"]
    search_fields = ["name", "description", "filename"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "validate", "validate_content"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    def _validate_python(self, content):
        """Run syntax + AST security checks, return a Response."""
        try:
            ast.parse(content)
        except SyntaxError as exc:
            return Response({
                "valid": False,
                "errors": [{"line": exc.lineno or 1, "message": f"Syntax error: {exc.msg}"}],
            })

        from .ast_validator import validate_custom_rule_ast

        errors = validate_custom_rule_ast(content)
        if errors:
            return Response({"valid": False, "errors": errors})

        return Response({"valid": True, "errors": []})

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        rule = self.get_object()
        return self._validate_python(rule.content)

    @action(detail=False, methods=["post"], url_path="validate-content")
    def validate_content(self, request):
        content = request.data.get("content")
        if not content:
            return Response(
                {"content": ["This field is required."]},
                status=400,
            )
        return self._validate_python(content)
