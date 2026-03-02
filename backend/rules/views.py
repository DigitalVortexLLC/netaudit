import json
import subprocess
import sys
import time

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
from audit_runner.scaffold import cleanup_scaffold, create_test_scaffold
from audits.services import _fetch_config
from devices.models import Device

from .ast_validator import validate_custom_rule_ast
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
        if self.action in ("list", "retrieve", "validate", "validate_content", "test_run"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    def _validate_python(self, content):
        """Run syntax + AST security checks, return a Response."""
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

    @action(detail=False, methods=["post"], url_path="test-run")
    def test_run(self, request):
        content = request.data.get("content")
        device_id = request.data.get("device_id")

        if not content:
            return Response(
                {"content": ["This field is required."]},
                status=400,
            )
        if not device_id:
            return Response(
                {"device_id": ["This field is required."]},
                status=400,
            )

        # Validate the rule content via AST checks
        errors = validate_custom_rule_ast(content)
        if errors:
            return Response({
                "passed": False,
                "output": "\n".join(f"Line {e['line']}: {e['message']}" for e in errors),
                "duration": 0.0,
                "summary": {},
                "validation_errors": errors,
            })

        # Fetch the device and its config
        try:
            device = Device.objects.get(pk=device_id)
        except Device.DoesNotExist:
            return Response(
                {"error": f"Device with id {device_id} not found."},
                status=404,
            )

        try:
            config_text = _fetch_config(device)
        except Exception as exc:
            return Response(
                {"error": f"Failed to fetch device config: {exc}"},
                status=502,
            )

        scaffold_path = None
        try:
            scaffold_path = create_test_scaffold(config_text, content)
            report_file = scaffold_path / "report.json"

            start = time.monotonic()
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(scaffold_path),
                    "--json-report",
                    f"--json-report-file={report_file}",
                    "-v",
                    "--tb=short",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            duration = round(time.monotonic() - start, 3)

            # Parse the JSON report
            if report_file.exists():
                report = json.loads(report_file.read_text())
            else:
                return Response({
                    "passed": False,
                    "output": result.stderr or "pytest failed to produce a report",
                    "duration": duration,
                    "summary": {},
                })

            tests = report.get("tests", [])
            summary = report.get("summary", {})
            passed = all(t.get("outcome") == "passed" for t in tests) and len(tests) > 0

            # Build output lines
            output_lines = []
            for t in tests:
                node_id = t.get("nodeid", "")
                outcome = t.get("outcome", "unknown")
                line = f"{node_id} :: {outcome}"
                if outcome == "failed":
                    longrepr = t.get("call", {}).get("longrepr", "")
                    if longrepr:
                        line += f"\n{longrepr}"
                output_lines.append(line)

            return Response({
                "passed": passed,
                "output": "\n".join(output_lines),
                "duration": duration,
                "summary": summary,
            })

        except subprocess.TimeoutExpired:
            return Response({
                "passed": False,
                "output": "Test run timed out after 30 seconds.",
                "duration": 30.0,
                "summary": {},
            })
        except Exception as exc:
            return Response({
                "passed": False,
                "output": f"Test run failed: {exc}",
                "duration": 0.0,
                "summary": {},
            })
        finally:
            if scaffold_path is not None:
                cleanup_scaffold(scaffold_path)
