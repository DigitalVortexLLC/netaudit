# Custom Rule Editor Redesign + Security Sandboxing

**Date:** 2026-03-01

## Overview

Redesign the Custom Rule create/edit page with a split-panel layout (form inputs on the left, Monaco code editor on the right) and add AST-based security sandboxing to prevent arbitrary code execution.

## Part 1: Split-Panel Layout

### Left Panel (~40%) — Form Metadata

Card containing:
- Name (text input, required)
- Description (textarea)
- Filename (text input, required, must start with `test_` and end with `.py`)
- Severity (select: critical/high/medium/low/info)
- Enabled (checkbox)
- Device (optional select)
- Group (optional select)
- Create/Update + Cancel buttons at bottom

### Right Panel (~60%) — Monaco Editor

- Python syntax highlighting with VS Code dark theme
- Toolbar: filename badge, **Validate** button, line/column indicator
- Inline red squiggly markers on validation errors (via `setModelMarkers`)
- On validation success, green toast/indicator
- Min height ~500px, fills available vertical space

### Responsive Behavior

On screens < 1024px, panels stack vertically: form on top, editor below.

## Part 2: Backend Security — AST Allowlist

### Problem

Custom rules execute via `subprocess.run([python, -m, pytest, ...])` with full access to filesystem, network, environment variables, and Django ORM. Any Editor-role user can execute arbitrary code.

### Solution: Static AST Analysis

An AST visitor walks the code at save and validate time, rejecting anything not in the allowlist.

### Allowed Imports

- `pytest`
- `re`
- `json`
- `ipaddress`

### Allowed Builtins

`assert`, `len`, `str`, `int`, `float`, `bool`, `list`, `dict`, `set`, `tuple`, `sorted`, `enumerate`, `range`, `zip`, `map`, `filter`, `any`, `all`, `min`, `max`, `isinstance`, `hasattr`, `print`, `True`, `False`, `None`

### Blocked Patterns

- Any `import` / `from ... import` not in the allowlist
- `eval()`, `exec()`, `compile()`, `__import__()`, `globals()`, `locals()`
- `open()`, `file()`, any file I/O
- `os.*`, `subprocess.*`, `sys.*`, `socket.*`
- `getattr()`, `setattr()` (prevents dynamic attribute traversal)
- `__builtins__`, `__class__`, `__subclasses__`, `__bases__` dunder access
- `breakpoint()`, `exit()`, `quit()`

### Validation Error Format

Errors include line number so the frontend can show inline markers:

```json
{
  "content": ["Line 3: Import 'os' is not allowed. Allowed imports: pytest, re, json, ipaddress"]
}
```

### Enforcement Points

1. `CustomRuleSerializer.validate_content()` — runs on create/update
2. `/api/v1/rules/custom/{id}/validate/` — runs on explicit validate

## Part 3: Frontend — Monaco Integration

### Package

`@monaco-editor/react` — standard React wrapper for Monaco Editor

### Integration

- Replace the Content `<Textarea>` with Monaco `<Editor>` component
- Language set to `python`, theme set to `vs-dark`
- Editor value syncs to `formData.content` via `onChange`
- Validation errors mapped to `monaco.editor.setModelMarkers()` for red squiggles
- Validate button available for both create and edit modes (validates content via API or locally)

## Files to Modify

### Backend
- `backend/rules/serializers.py` — add AST validation logic
- `backend/rules/views.py` — update validate endpoint to work for new rules (not just existing)

### Frontend
- `frontend/src/pages/rules/custom-form.tsx` — redesign layout, integrate Monaco
- `frontend/package.json` — add `@monaco-editor/react`

### New Files
- `backend/rules/ast_validator.py` — AST allowlist walker (new module)
