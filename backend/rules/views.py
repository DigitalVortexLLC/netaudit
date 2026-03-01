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
        if self.action in ("list", "retrieve", "validate"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        rule = self.get_object()
        try:
            ast.parse(rule.content)
            return Response({"valid": True})
        except SyntaxError as exc:
            return Response({"valid": False, "error": str(exc)})
