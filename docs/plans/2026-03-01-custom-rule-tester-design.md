# Custom Rule Page Redesign + Rule Tester

## Overview

Reorganize the custom rule form page from a left-sidebar/right-editor layout into a two-row layout, and add a rule tester that executes custom Python rules against device configs on the backend.

## Layout

### Row 1 (top, fills available height)

Two side-by-side panels:

- **Left — Monaco Code Editor**: Python editor with validate button (existing functionality preserved)
- **Right — Rule Tester**: Select a device, click "Test" to run the rule against the device's config on the backend. Shows pass/fail result and the device config.

### Row 2 (bottom, compact)

Horizontal grid of form fields: name, description, filename, severity, enabled, device, group, and submit/cancel buttons.

## Backend

New endpoint: `POST /rules/custom/test-run/`

Request:
```json
{
  "content": "import pytest\ndef test_example(device_config): ...",
  "device_id": 42
}
```

Response:
```json
{
  "passed": true,
  "output": "",
  "duration": 0.234
}
```

On failure:
```json
{
  "passed": false,
  "output": "AssertionError: 'ntp server' not found in config",
  "duration": 0.156
}
```

Implementation:
1. Validate the content via AST validator
2. Fetch device config via existing `_fetch_config()` or device model
3. Create a minimal temp pytest scaffold (reuse `audit_runner/scaffold.py` patterns)
4. Run pytest with `--json-report` on just that single file
5. Parse result and return pass/fail + output

## Frontend

- Reorganize `custom-form.tsx` layout to two rows
- Add test panel with device selector, test button, result display
- Add `useTestCustomRuleContent` hook calling the new endpoint
- Show device config in a code-style display after test runs
