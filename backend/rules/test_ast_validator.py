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

    def test_re_compile_allowed(self):
        code = (
            "import re\n\n"
            "def test_x(device_config):\n"
            "    pattern = re.compile(r'ntp server \\S+')\n"
            "    assert pattern.search(device_config)\n"
        )
        errors = validate_custom_rule_ast(code)
        self.assertEqual(errors, [])

    def test_json_loads_allowed(self):
        code = (
            "import json\n\n"
            "def test_x():\n"
            "    data = json.loads('{\"key\": \"value\"}')\n"
            "    assert data['key'] == 'value'\n"
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

    def test_relative_import_blocked(self):
        errors = validate_custom_rule_ast("from . import something\n")
        self.assertTrue(len(errors) > 0)
        self.assertIn("Relative import", errors[0]["message"])


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


class SyntaxErrorTests(SimpleTestCase):
    """Syntax errors should be returned as structured error dicts."""

    def test_syntax_error_returns_error(self):
        errors = validate_custom_rule_ast("def test_x(\n    assert True\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("Syntax error", errors[0]["message"])
        self.assertIsInstance(errors[0]["line"], int)

    def test_empty_source_is_valid(self):
        errors = validate_custom_rule_ast("")
        self.assertEqual(errors, [])


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
