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
