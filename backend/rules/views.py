import ast

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CustomRule, SimpleRule
from .serializers import CustomRuleSerializer, SimpleRuleSerializer


class SimpleRuleViewSet(viewsets.ModelViewSet):
    queryset = SimpleRule.objects.all()
    serializer_class = SimpleRuleSerializer
    filterset_fields = ["device", "enabled", "severity", "rule_type"]
    search_fields = ["name", "description", "pattern"]


class CustomRuleViewSet(viewsets.ModelViewSet):
    queryset = CustomRule.objects.all()
    serializer_class = CustomRuleSerializer
    filterset_fields = ["device", "enabled", "severity"]
    search_fields = ["name", "description", "filename"]

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        rule = self.get_object()
        try:
            ast.parse(rule.content)
            return Response({"valid": True})
        except SyntaxError as exc:
            return Response({"valid": False, "error": str(exc)})
