# Custom Rule Editor + AST Sandboxing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the custom rule form into a split-panel layout with Monaco Editor and add AST-based security validation to prevent arbitrary code execution.

**Architecture:** Backend gets a new `ast_validator.py` module that walks the AST of user-submitted Python code, rejecting any imports/calls/attributes not in an allowlist. The serializer and validate endpoint both call this validator. Frontend replaces the single-column form with a two-column layout (form metadata left, Monaco editor right) and maps validation errors to inline editor markers.

**Tech Stack:** Django REST Framework (backend validation), `@monaco-editor/react` (code editor), TailwindCSS (layout), React 19 + TypeScript

---

### Task 1: Create AST Validator Module — Tests

**Files:**
- Create: `backend/rules/test_ast_validator.py`

**Step 1: Write failing tests for the AST validator**

```python
"""Tests for rules.ast_validator — allowlist-based Python code security checker."""

from django.test import SimpleTestCase

from rules.ast_validator import validate_custom_rule_ast


class AllowedCodeTests(SimpleTestCase):
    """Code that SHOULD pass validation."""

    def test_simple_assert(self):
        errors = validate_custom_rule_ast("def test_ntp(device_config):\n    assert 'ntp' in device_config\n")
        self.assertEqual(errors, [])

    def test_import_pytest(self):
        errors = validate_custom_rule_ast("import pytest\n\ndef test_x():\n    pytest.skip('reason')\n")
        self.assertEqual(errors, [])

    def test_import_re(self):
        errors = validate_custom_rule_ast("import re\n\ndef test_x(device_config):\n    assert re.search(r'ntp', device_config)\n")
        self.assertEqual(errors, [])

    def test_import_json(self):
        errors = validate_custom_rule_ast("import json\n\ndef test_x():\n    data = json.loads('{}')\n    assert data == {}\n")
        self.assertEqual(errors, [])

    def test_import_ipaddress(self):
        errors = validate_custom_rule_ast("import ipaddress\n\ndef test_x():\n    addr = ipaddress.ip_address('10.0.0.1')\n    assert addr.is_private\n")
        self.assertEqual(errors, [])

    def test_from_import_allowed(self):
        errors = validate_custom_rule_ast("from re import search\n\ndef test_x(device_config):\n    assert search(r'ntp', device_config)\n")
        self.assertEqual(errors, [])

    def test_allowed_builtins(self):
        code = (
            "def test_x(device_config):\n"
            "    lines = device_config.split('\\n')\n"
            "    assert len(lines) > 0\n"
            "    assert isinstance(lines, list)\n"
            "    nums = [int(x) for x in ['1', '2']]\n"
            "    assert sorted(nums) == [1, 2]\n"
        )
        errors = validate_custom_rule_ast(code)
        self.assertEqual(errors, [])

    def test_pytest_mark_parametrize(self):
        code = (
            "import pytest\n\n"
            "@pytest.mark.parametrize('val', [1, 2])\n"
            "def test_x(val):\n"
            "    assert val > 0\n"
        )
        errors = validate_custom_rule_ast(code)
        self.assertEqual(errors, [])

    def test_string_methods_allowed(self):
        code = (
            "def test_x(device_config):\n"
            "    assert device_config.strip().startswith('hostname')\n"
        )
        errors = validate_custom_rule_ast(code)
        self.assertEqual(errors, [])


class BlockedImportTests(SimpleTestCase):
    """Import statements that MUST be rejected."""

    def test_import_os(self):
        errors = validate_custom_rule_ast("import os\n\ndef test_x():\n    os.system('ls')\n")
        self.assertTrue(len(errors) > 0)
        self.assertIn("os", errors[0]["message"])
        self.assertEqual(errors[0]["line"], 1)

    def test_import_subprocess(self):
        errors = validate_custom_rule_ast("import subprocess\n")
        self.assertTrue(len(errors) > 0)
        self.assertIn("subprocess", errors[0]["message"])

    def test_import_sys(self):
        errors = validate_custom_rule_ast("import sys\n")
        self.assertTrue(len(errors) > 0)

    def test_import_socket(self):
        errors = validate_custom_rule_ast("import socket\n")
        self.assertTrue(len(errors) > 0)

    def test_import_shutil(self):
        errors = validate_custom_rule_ast("import shutil\n")
        self.assertTrue(len(errors) > 0)

    def test_import_requests(self):
        errors = validate_custom_rule_ast("import requests\n")
        self.assertTrue(len(errors) > 0)

    def test_from_os_import(self):
        errors = validate_custom_rule_ast("from os import path\n")
        self.assertTrue(len(errors) > 0)
        self.assertIn("os", errors[0]["message"])

    def test_from_os_path_import(self):
        errors = validate_custom_rule_ast("from os.path import join\n")
        self.assertTrue(len(errors) > 0)

    def test_import_pathlib(self):
        errors = validate_custom_rule_ast("import pathlib\n")
        self.assertTrue(len(errors) > 0)

    def test_import_io(self):
        errors = validate_custom_rule_ast("import io\n")
        self.assertTrue(len(errors) > 0)


class BlockedCallTests(SimpleTestCase):
    """Function calls that MUST be rejected."""

    def test_eval(self):
        errors = validate_custom_rule_ast("def test_x():\n    eval('1+1')\n")
        self.assertTrue(len(errors) > 0)
        self.assertIn("eval", errors[0]["message"])

    def test_exec(self):
        errors = validate_custom_rule_ast("def test_x():\n    exec('pass')\n")
        self.assertTrue(len(errors) > 0)

    def test_compile(self):
        errors = validate_custom_rule_ast("def test_x():\n    compile('pass', '<string>', 'exec')\n")
        self.assertTrue(len(errors) > 0)

    def test___import__(self):
        errors = validate_custom_rule_ast("def test_x():\n    __import__('os')\n")
        self.assertTrue(len(errors) > 0)

    def test_open(self):
        errors = validate_custom_rule_ast("def test_x():\n    open('/etc/passwd')\n")
        self.assertTrue(len(errors) > 0)

    def test_globals(self):
        errors = validate_custom_rule_ast("def test_x():\n    globals()\n")
        self.assertTrue(len(errors) > 0)

    def test_locals(self):
        errors = validate_custom_rule_ast("def test_x():\n    locals()\n")
        self.assertTrue(len(errors) > 0)

    def test_getattr(self):
        errors = validate_custom_rule_ast("def test_x():\n    getattr(object, '__class__')\n")
        self.assertTrue(len(errors) > 0)

    def test_setattr(self):
        errors = validate_custom_rule_ast("def test_x():\n    setattr(object, 'x', 1)\n")
        self.assertTrue(len(errors) > 0)

    def test_delattr(self):
        errors = validate_custom_rule_ast("def test_x():\n    delattr(object, 'x')\n")
        self.assertTrue(len(errors) > 0)

    def test_breakpoint(self):
        errors = validate_custom_rule_ast("def test_x():\n    breakpoint()\n")
        self.assertTrue(len(errors) > 0)

    def test_exit(self):
        errors = validate_custom_rule_ast("def test_x():\n    exit()\n")
        self.assertTrue(len(errors) > 0)

    def test_quit(self):
        errors = validate_custom_rule_ast("def test_x():\n    quit()\n")
        self.assertTrue(len(errors) > 0)

    def test_input(self):
        errors = validate_custom_rule_ast("def test_x():\n    input('>')\n")
        self.assertTrue(len(errors) > 0)


class BlockedAttributeTests(SimpleTestCase):
    """Dunder attribute access that MUST be rejected."""

    def test___class__(self):
        errors = validate_custom_rule_ast("def test_x():\n    x = ''.__class__\n")
        self.assertTrue(len(errors) > 0)
        self.assertIn("__class__", errors[0]["message"])

    def test___subclasses__(self):
        errors = validate_custom_rule_ast("def test_x():\n    x = object.__subclasses__()\n")
        self.assertTrue(len(errors) > 0)

    def test___bases__(self):
        errors = validate_custom_rule_ast("def test_x():\n    x = type.__bases__\n")
        self.assertTrue(len(errors) > 0)

    def test___builtins__(self):
        errors = validate_custom_rule_ast("def test_x():\n    x = __builtins__\n")
        self.assertTrue(len(errors) > 0)

    def test___globals__(self):
        errors = validate_custom_rule_ast("def test_x():\n    x = test_x.__globals__\n")
        self.assertTrue(len(errors) > 0)

    def test___code__(self):
        errors = validate_custom_rule_ast("def test_x():\n    x = test_x.__code__\n")
        self.assertTrue(len(errors) > 0)


class MultipleErrorsTests(SimpleTestCase):
    """Validation should collect ALL errors, not stop at the first one."""

    def test_multiple_violations(self):
        code = "import os\nimport subprocess\n\ndef test_x():\n    eval('bad')\n"
        errors = validate_custom_rule_ast(code)
        self.assertGreaterEqual(len(errors), 3)

    def test_error_format(self):
        errors = validate_custom_rule_ast("import os\n")
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertIn("line", error)
        self.assertIn("message", error)
        self.assertIsInstance(error["line"], int)
        self.assertIsInstance(error["message"], str)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/test_ast_validator.py -v --no-header 2>&1 | head -20`
Expected: ImportError — `rules.ast_validator` does not exist yet

**Step 3: Commit test file**

```bash
git add backend/rules/test_ast_validator.py
git commit -m "test: add tests for AST-based custom rule validator"
```

---

### Task 2: Create AST Validator Module — Implementation

**Files:**
- Create: `backend/rules/ast_validator.py`

**Step 1: Implement the AST validator**

```python
"""
AST-based security validator for custom rule Python code.

Walks the AST and rejects any imports, function calls, or attribute access
that are not in the allowlist. Returns a list of error dicts with line numbers
so the frontend can display inline markers.
"""

import ast

ALLOWED_IMPORTS = frozenset({"pytest", "re", "json", "ipaddress"})

BLOCKED_CALLS = frozenset({
    "eval", "exec", "compile", "__import__",
    "open", "file",
    "globals", "locals",
    "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit", "input",
    "memoryview", "vars", "dir",
})

BLOCKED_DUNDER_ATTRS = frozenset({
    "__class__", "__subclasses__", "__bases__", "__mro__",
    "__builtins__", "__globals__", "__code__", "__closure__",
    "__import__", "__loader__", "__spec__",
})


def validate_custom_rule_ast(source: str) -> list[dict]:
    """
    Validate Python source code against the custom rule allowlist.

    Parameters
    ----------
    source : str
        The Python source code to validate.

    Returns
    -------
    list[dict]
        A list of error dicts, each with ``line`` (int) and ``message`` (str).
        An empty list means the code is safe.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [{"line": exc.lineno or 1, "message": f"Syntax error: {exc.msg}"}]

    errors = []
    for node in ast.walk(tree):
        _check_import(node, errors)
        _check_call(node, errors)
        _check_attribute(node, errors)
        _check_name(node, errors)

    return errors


def _check_import(node: ast.AST, errors: list[dict]) -> None:
    """Reject any import not in the allowlist."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            root_module = alias.name.split(".")[0]
            if root_module not in ALLOWED_IMPORTS:
                errors.append({
                    "line": node.lineno,
                    "message": (
                        f"Import '{alias.name}' is not allowed. "
                        f"Allowed imports: {', '.join(sorted(ALLOWED_IMPORTS))}"
                    ),
                })
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            root_module = node.module.split(".")[0]
            if root_module not in ALLOWED_IMPORTS:
                errors.append({
                    "line": node.lineno,
                    "message": (
                        f"Import from '{node.module}' is not allowed. "
                        f"Allowed imports: {', '.join(sorted(ALLOWED_IMPORTS))}"
                    ),
                })


def _check_call(node: ast.AST, errors: list[dict]) -> None:
    """Reject calls to blocked builtin functions."""
    if not isinstance(node, ast.Call):
        return

    func = node.func
    name = None

    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr

    if name and name in BLOCKED_CALLS:
        errors.append({
            "line": node.lineno,
            "message": f"Call to '{name}()' is not allowed.",
        })


def _check_attribute(node: ast.AST, errors: list[dict]) -> None:
    """Reject access to blocked dunder attributes."""
    if isinstance(node, ast.Attribute):
        if node.attr in BLOCKED_DUNDER_ATTRS:
            errors.append({
                "line": node.lineno,
                "message": (
                    f"Access to '{node.attr}' is not allowed."
                ),
            })


def _check_name(node: ast.AST, errors: list[dict]) -> None:
    """Reject direct references to blocked dunder names."""
    if isinstance(node, ast.Name):
        if node.id in BLOCKED_DUNDER_ATTRS:
            errors.append({
                "line": node.lineno,
                "message": (
                    f"Reference to '{node.id}' is not allowed."
                ),
            })
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/test_ast_validator.py -v --no-header`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/rules/ast_validator.py
git commit -m "feat: add AST-based security validator for custom rules"
```

---

### Task 3: Integrate AST Validator into Serializer and View

**Files:**
- Modify: `backend/rules/serializers.py:30-37` (replace `validate_content`)
- Modify: `backend/rules/views.py:36-43` (replace validate action)

**Step 1: Write failing tests for the integration**

Add to `backend/rules/tests.py` — new test class after the existing `CustomRuleAPITests`:

```python
# Add at top of file:
# (no new imports needed — ValidationError, TestCase, reverse, status, APITestCase already imported)

# Add new test class after CustomRuleGroupAPITests at end of file:

class CustomRuleASTValidationAPITests(APITestCase):
    """Tests that the API rejects dangerous code via AST validation."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="astuser", email="ast@test.com", password="testpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("customrule-list")
        self.base_payload = {
            "name": "Test Rule",
            "description": "",
            "filename": "test_rule.py",
            "severity": "medium",
            "enabled": True,
        }

    def test_create_rejects_import_os(self):
        payload = {**self.base_payload, "content": "import os\n\ndef test_x():\n    os.system('ls')\n"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_create_rejects_eval(self):
        payload = {**self.base_payload, "content": "def test_x():\n    eval('1')\n"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_create_rejects_open(self):
        payload = {**self.base_payload, "content": "def test_x():\n    open('/etc/passwd')\n"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_allows_safe_code(self):
        payload = {**self.base_payload, "content": "import re\n\ndef test_x(device_config):\n    assert re.search(r'ntp', device_config)\n"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_rejects_dangerous_code(self):
        payload = {**self.base_payload, "content": "def test_x(): pass\n"}
        response = self.client.post(self.list_url, payload, format="json")
        rule_id = response.data["id"]
        url = reverse("customrule-detail", args=[rule_id])
        bad_payload = {**self.base_payload, "content": "import subprocess\n\ndef test_x():\n    subprocess.run(['ls'])\n"}
        response = self.client.put(url, bad_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_endpoint_returns_ast_errors(self):
        payload = {**self.base_payload, "content": "import os\n\ndef test_x():\n    os.system('ls')\n"}
        # Create via ORM (bypassing serializer) to test validate endpoint
        from rules.models import CustomRule
        rule = CustomRule.objects.create(**payload)
        url = reverse("customrule-validate", args=[rule.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["valid"])
        self.assertIn("errors", response.data)
        self.assertTrue(len(response.data["errors"]) > 0)
        self.assertIn("line", response.data["errors"][0])
        self.assertIn("message", response.data["errors"][0])

    def test_validate_endpoint_valid_code(self):
        payload = {**self.base_payload, "content": "def test_x(device_config):\n    assert 'ntp' in device_config\n"}
        from rules.models import CustomRule
        rule = CustomRule.objects.create(**payload)
        url = reverse("customrule-validate", args=[rule.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])

    def test_error_message_includes_line_number(self):
        payload = {**self.base_payload, "content": "import os\n"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_text = str(response.data["content"])
        self.assertIn("Line 1", error_text)
```

**Step 2: Run new tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/tests.py::CustomRuleASTValidationAPITests -v --no-header`
Expected: FAIL — serializer still only checks syntax, not AST security

**Step 3: Update serializer — `backend/rules/serializers.py`**

Replace `validate_content` (lines 30-37) with:

```python
    def validate_content(self, value):
        try:
            ast.parse(value)
        except SyntaxError as exc:
            raise serializers.ValidationError(
                f"Invalid Python syntax: {exc}"
            )

        from .ast_validator import validate_custom_rule_ast

        errors = validate_custom_rule_ast(value)
        if errors:
            messages = [
                f"Line {e['line']}: {e['message']}" for e in errors
            ]
            raise serializers.ValidationError(messages)

        return value
```

**Step 4: Update validate endpoint — `backend/rules/views.py`**

Replace the validate action (lines 36-43) with:

```python
    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        rule = self.get_object()
        try:
            ast.parse(rule.content)
        except SyntaxError as exc:
            return Response({
                "valid": False,
                "errors": [{"line": exc.lineno or 1, "message": f"Syntax error: {exc.msg}"}],
            })

        from rules.ast_validator import validate_custom_rule_ast

        errors = validate_custom_rule_ast(rule.content)
        if errors:
            return Response({"valid": False, "errors": errors})

        return Response({"valid": True, "errors": []})
```

**Step 5: Run ALL rules tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/ -v --no-header`
Expected: All tests PASS (existing + new)

**Step 6: Commit**

```bash
git add backend/rules/serializers.py backend/rules/views.py backend/rules/tests.py
git commit -m "feat: integrate AST validator into serializer and validate endpoint"
```

---

### Task 4: Add Validate-Content Endpoint (for unsaved rules)

The current validate endpoint requires an existing rule (`detail=True`). For the "New Rule" form, we need to validate content before saving.

**Files:**
- Modify: `backend/rules/views.py` (add new action)
- Modify: `backend/rules/urls.py` (if needed for custom routing)

**Step 1: Write failing test**

Add to `backend/rules/tests.py`:

```python
class CustomRuleValidateContentAPITests(APITestCase):
    """Tests for POST /api/v1/rules/custom/validate-content/ (no saved rule needed)."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="valuser", email="val@test.com", password="testpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("customrule-validate-content")

    def test_valid_code(self):
        response = self.client.post(self.url, {"content": "def test_x(device_config):\n    assert 'ntp' in device_config\n"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["errors"], [])

    def test_syntax_error(self):
        response = self.client.post(self.url, {"content": "def test_x(\n    assert True\n"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["valid"])
        self.assertTrue(len(response.data["errors"]) > 0)

    def test_blocked_import(self):
        response = self.client.post(self.url, {"content": "import os\n"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["valid"])

    def test_missing_content_field(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

**Step 2: Run to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/tests.py::CustomRuleValidateContentAPITests -v --no-header`
Expected: FAIL — URL `customrule-validate-content` does not exist

**Step 3: Add the endpoint to views.py**

Add a new `validate_content` action to `CustomRuleViewSet`:

```python
    @action(detail=False, methods=["post"], url_path="validate-content")
    def validate_content(self, request):
        content = request.data.get("content")
        if not content:
            return Response(
                {"content": ["This field is required."]},
                status=400,
            )

        try:
            ast.parse(content)
        except SyntaxError as exc:
            return Response({
                "valid": False,
                "errors": [{"line": exc.lineno or 1, "message": f"Syntax error: {exc.msg}"}],
            })

        from rules.ast_validator import validate_custom_rule_ast

        errors = validate_custom_rule_ast(content)
        if errors:
            return Response({"valid": False, "errors": errors})

        return Response({"valid": True, "errors": []})
```

Also update `get_permissions` to allow viewers to access `validate_content`:

```python
    def get_permissions(self):
        if self.action in ("list", "retrieve", "validate", "validate_content"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
```

**Step 4: Run tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/ -v --no-header`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/rules/views.py backend/rules/tests.py
git commit -m "feat: add validate-content endpoint for unsaved custom rules"
```

---

### Task 5: Install Monaco Editor

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install the package**

Run: `cd /Users/aaronroth/Documents/netaudit/frontend && npm install @monaco-editor/react`

**Step 2: Verify it installed**

Run: `cd /Users/aaronroth/Documents/netaudit/frontend && node -e "require('@monaco-editor/react'); console.log('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add @monaco-editor/react dependency"
```

---

### Task 6: Add Frontend Validation Hook

**Files:**
- Modify: `frontend/src/hooks/use-rules.ts` (add `useValidateCustomRuleContent` hook)

**Step 1: Add the new hook**

Append to `frontend/src/hooks/use-rules.ts`:

```typescript
export function useValidateCustomRuleContent() {
  return useMutation({
    mutationFn: async (content: string) => {
      const response = await api.post<{
        valid: boolean;
        errors: Array<{ line: number; message: string }>;
      }>("/rules/custom/validate-content/", { content });
      return response.data;
    },
  });
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/use-rules.ts
git commit -m "feat: add useValidateCustomRuleContent hook"
```

---

### Task 7: Redesign Custom Rule Form — Split Layout with Monaco

**Files:**
- Modify: `frontend/src/pages/rules/custom-form.tsx` (full rewrite of the component)

**Step 1: Rewrite the component**

Replace the entire file with the new split-panel layout. Key changes:

1. Import `Editor` from `@monaco-editor/react` and `monaco` types
2. Split layout: left panel (form fields in a card) + right panel (Monaco editor)
3. Use `useRef` for Monaco editor instance to set markers
4. Add Validate button that calls `useValidateCustomRuleContent` and maps errors to `setModelMarkers`
5. Responsive: stack on `< lg` screens via Tailwind `flex-col lg:flex-row`

```tsx
import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Play, CheckCircle2, XCircle } from "lucide-react";
import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor as monacoEditor } from "monaco-editor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  useCustomRule,
  useCreateCustomRule,
  useUpdateCustomRule,
  useValidateCustomRuleContent,
} from "@/hooks/use-rules";
import { useDevices } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";
import type { CustomRuleFormData, Severity } from "@/types";

const DEFAULT_CONTENT = `import pytest


def test_example(device_config):
    """Check that the device config contains expected configuration."""
    assert "hostname" in device_config
`;

export function CustomRuleFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: rule, isLoading: ruleLoading } = useCustomRule(Number(id));
  const { data: devicesData } = useDevices();
  const { data: groupsData } = useGroups();
  const createRule = useCreateCustomRule();
  const updateRule = useUpdateCustomRule(Number(id));
  const validateContent = useValidateCustomRuleContent();

  const [formData, setFormData] = useState<CustomRuleFormData>({
    name: "",
    description: "",
    filename: "",
    content: DEFAULT_CONTENT,
    severity: "medium",
    enabled: true,
    device: null,
    group: null,
  });

  const [validationState, setValidationState] = useState<
    "idle" | "valid" | "invalid"
  >("idle");
  const [validationErrors, setValidationErrors] = useState<
    Array<{ line: number; message: string }>
  >([]);

  const editorRef = useRef<monacoEditor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof import("monaco-editor") | null>(null);

  useEffect(() => {
    if (rule) {
      setFormData({
        name: rule.name,
        description: rule.description,
        filename: rule.filename,
        content: rule.content,
        severity: rule.severity,
        enabled: rule.enabled,
        device: rule.device,
        group: rule.group,
      });
    }
  }, [rule]);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco as unknown as typeof import("monaco-editor");
  };

  function setEditorMarkers(
    errors: Array<{ line: number; message: string }>
  ) {
    if (!editorRef.current || !monacoRef.current) return;
    const model = editorRef.current.getModel();
    if (!model) return;

    const markers: monacoEditor.IMarkerData[] = errors.map((err) => ({
      severity: monacoRef.current!.MarkerSeverity.Error,
      startLineNumber: err.line,
      startColumn: 1,
      endLineNumber: err.line,
      endColumn: model.getLineMaxColumn(err.line),
      message: err.message,
    }));

    monacoRef.current.editor.setModelMarkers(model, "ast-validator", markers);
  }

  function clearEditorMarkers() {
    if (!editorRef.current || !monacoRef.current) return;
    const model = editorRef.current.getModel();
    if (!model) return;
    monacoRef.current.editor.setModelMarkers(model, "ast-validator", []);
  }

  function handleValidate() {
    setValidationState("idle");
    setValidationErrors([]);
    clearEditorMarkers();

    validateContent.mutate(formData.content, {
      onSuccess: (data) => {
        if (data.valid) {
          setValidationState("valid");
          setValidationErrors([]);
          clearEditorMarkers();
        } else {
          setValidationState("invalid");
          setValidationErrors(data.errors);
          setEditorMarkers(data.errors);
        }
      },
      onError: () => {
        setValidationState("invalid");
        setValidationErrors([{ line: 1, message: "Validation request failed" }]);
      },
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const mutation = isEdit ? updateRule : createRule;
    mutation.mutate(formData, {
      onSuccess: () => navigate("/rules/custom"),
    });
  }

  if (isEdit && ruleLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <Button variant="outline" size="sm" asChild>
          <Link to="/rules/custom">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">
          {isEdit ? "Edit Custom Rule" : "New Custom Rule"}
        </h1>
      </div>

      {/* Split Layout */}
      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
        {/* Left Panel — Form */}
        <Card className="lg:w-[380px] lg:shrink-0 overflow-y-auto">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Rule Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  rows={2}
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="filename">Filename</Label>
                <Input
                  id="filename"
                  value={formData.filename}
                  onChange={(e) =>
                    setFormData({ ...formData, filename: e.target.value })
                  }
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Must start with test_ and end with .py
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="severity">Severity</Label>
                <select
                  id="severity"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={formData.severity}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      severity: e.target.value as Severity,
                    })
                  }
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                  <option value="info">Info</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  id="enabled"
                  checked={formData.enabled}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, enabled: checked === true })
                  }
                />
                <Label htmlFor="enabled">Enabled</Label>
              </div>

              <div className="space-y-2">
                <Label htmlFor="device">Device</Label>
                <select
                  id="device"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={formData.device ?? ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      device: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                >
                  <option value="">None</option>
                  {devicesData?.results.map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="group">Group</Label>
                <select
                  id="group"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={formData.group ?? ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      group: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                >
                  <option value="">None</option>
                  {groupsData?.results.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  type="submit"
                  disabled={createRule.isPending || updateRule.isPending}
                >
                  {createRule.isPending || updateRule.isPending
                    ? "Saving..."
                    : isEdit
                      ? "Update Rule"
                      : "Create Rule"}
                </Button>
                <Button variant="outline" type="button" asChild>
                  <Link to="/rules/custom">Cancel</Link>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Right Panel — Editor */}
        <Card className="flex-1 flex flex-col min-h-[500px]">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base font-mono">
              {formData.filename || "test_rule.py"}
            </CardTitle>
            <div className="flex items-center gap-2">
              {validationState === "valid" && (
                <span className="flex items-center gap-1 text-sm text-green-500">
                  <CheckCircle2 className="h-4 w-4" />
                  Valid
                </span>
              )}
              {validationState === "invalid" && (
                <span className="flex items-center gap-1 text-sm text-red-500">
                  <XCircle className="h-4 w-4" />
                  {validationErrors.length} error{validationErrors.length !== 1 ? "s" : ""}
                </span>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleValidate}
                disabled={validateContent.isPending}
              >
                <Play className="mr-1 h-3 w-3" />
                {validateContent.isPending ? "Validating..." : "Validate"}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 overflow-hidden">
            <Editor
              defaultLanguage="python"
              theme="vs-dark"
              value={formData.content}
              onChange={(value) =>
                setFormData({ ...formData, content: value ?? "" })
              }
              onMount={handleEditorDidMount}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                insertSpaces: true,
                wordWrap: "off",
                padding: { top: 8 },
              }}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

**Step 2: Verify the frontend compiles**

Run: `cd /Users/aaronroth/Documents/netaudit/frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/pages/rules/custom-form.tsx
git commit -m "feat: redesign custom rule form with split layout and Monaco editor"
```

---

### Task 8: Visual Verification and Polish

**Step 1: Start the dev server and verify the layout**

Run the frontend dev server and check:
- Left panel shows all form fields
- Right panel shows Monaco editor with Python highlighting
- Validate button works and shows inline markers on errors
- Form submission works for both create and edit
- Responsive stacking works on narrow viewport

**Step 2: Fix any visual issues**

Adjust Tailwind classes, spacing, or editor options as needed.

**Step 3: Run all backend tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/ audits/ -v --no-header`
Expected: All PASS

**Step 4: Final commit if any polish changes were made**

```bash
git add -u
git commit -m "fix: polish custom rule editor layout and spacing"
```
