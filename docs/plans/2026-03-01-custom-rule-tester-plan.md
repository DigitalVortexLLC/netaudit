# Custom Rule Page Redesign + Rule Tester — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize the custom rule form into a two-row layout (editor+tester top, form fields bottom) and add a backend endpoint that executes custom Python rules against device configs.

**Architecture:** New DRF action on `CustomRuleViewSet` that builds a minimal pytest scaffold with a single custom rule file + device config, runs pytest, and returns pass/fail + output. Frontend reorganizes `custom-form.tsx` into two rows and adds a test panel mirroring the simple rule tester UX.

**Tech Stack:** Django REST Framework, pytest + pytest-json-report, React, Monaco Editor, TanStack Query

---

### Task 1: Backend — Add `test-run` action to CustomRuleViewSet

**Files:**
- Modify: `backend/rules/views.py`
- Modify: `backend/audit_runner/scaffold.py`

**Step 1: Add `create_test_scaffold` to `scaffold.py`**

Add a new function that creates a minimal scaffold for testing a single custom rule (no simple rules, no audit_run dependency):

```python
def create_test_scaffold(config_text, rule_content, rule_filename="test_rule.py"):
    """
    Build a minimal temporary pytest project for testing a single custom rule.
    """
    scaffold_path = Path(tempfile.mkdtemp(prefix="netaudit_test_"))

    (scaffold_path / "_config.txt").write_text(config_text)

    conftest_template = _env.get_template("conftest.py.j2")
    # Write a root conftest that only provides device_config
    root_conftest = (
        "import pytest\n"
        "from pathlib import Path\n\n"
        "CONFIG_FILE = Path(__file__).parent / '_config.txt'\n\n\n"
        "@pytest.fixture(scope='session')\n"
        "def device_config():\n"
        "    return CONFIG_FILE.read_text()\n"
    )
    (scaffold_path / "conftest.py").write_text(root_conftest)
    (scaffold_path / rule_filename).write_text(rule_content)

    return scaffold_path
```

**Step 2: Add `test_run` action to `CustomRuleViewSet` in `views.py`**

```python
import json
import subprocess
import sys
import time

from audit_runner.scaffold import cleanup_scaffold, create_test_scaffold
from audits.services import _fetch_config
from devices.models import Device
from rules.ast_validator import validate_custom_rule_ast

@action(detail=False, methods=["post"], url_path="test-run")
def test_run(self, request):
    content = request.data.get("content")
    device_id = request.data.get("device_id")

    if not content:
        return Response({"content": ["This field is required."]}, status=400)
    if not device_id:
        return Response({"device_id": ["This field is required."]}, status=400)

    # Validate AST first
    errors = validate_custom_rule_ast(content)
    if errors:
        return Response({
            "passed": False,
            "output": "\n".join(f"Line {e['line']}: {e['message']}" for e in errors),
            "duration": 0,
            "validation_errors": errors,
        })

    # Fetch device config
    try:
        device = Device.objects.get(pk=device_id)
        config_text = _fetch_config(device)
    except Device.DoesNotExist:
        return Response({"device_id": ["Device not found."]}, status=404)
    except Exception as exc:
        return Response({
            "passed": False,
            "output": f"Failed to fetch config: {exc}",
            "duration": 0,
        })

    # Create scaffold and run pytest
    scaffold_path = None
    try:
        scaffold_path = create_test_scaffold(config_text, content)
        report_file = scaffold_path / "report.json"

        start = time.monotonic()
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(scaffold_path),
                "--json-report",
                f"--json-report-file={report_file}",
                "-v", "--tb=short",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration = round(time.monotonic() - start, 3)

        if report_file.exists():
            report = json.loads(report_file.read_text())
        else:
            return Response({
                "passed": False,
                "output": result.stderr or "pytest failed to produce a report",
                "duration": duration,
            })

        tests = report.get("tests", [])
        all_passed = all(t.get("outcome") == "passed" for t in tests)

        output_lines = []
        for t in tests:
            outcome = t.get("outcome", "unknown")
            node_id = t.get("nodeid", "")
            test_name = node_id.split("::")[-1] if "::" in node_id else node_id
            if outcome == "passed":
                output_lines.append(f"PASSED: {test_name}")
            else:
                msg = ""
                call_info = t.get("call", {})
                if call_info:
                    msg = call_info.get("longrepr", "")
                    if not isinstance(msg, str):
                        msg = str(msg)
                output_lines.append(f"FAILED: {test_name}\n{msg}")

        return Response({
            "passed": all_passed,
            "output": "\n".join(output_lines),
            "duration": duration,
            "summary": report.get("summary", {}),
        })

    except subprocess.TimeoutExpired:
        return Response({
            "passed": False,
            "output": "Test execution timed out (30s limit)",
            "duration": 30,
        })
    except Exception as exc:
        return Response({
            "passed": False,
            "output": str(exc),
            "duration": 0,
        })
    finally:
        if scaffold_path:
            cleanup_scaffold(scaffold_path)
```

Also update `get_permissions` to include `"test_run"` in the viewer-allowed actions.

**Step 3: Run the backend to verify no import errors**

Run: `cd backend && python manage.py check`
Expected: System check identified no issues.

**Step 4: Commit**

```bash
git add backend/rules/views.py backend/audit_runner/scaffold.py
git commit -m "feat: add test-run endpoint for custom rules"
```

---

### Task 2: Frontend — Add `useTestCustomRuleContent` hook

**Files:**
- Modify: `frontend/src/hooks/use-rules.ts`

**Step 1: Add the hook**

Add at the end of `use-rules.ts`:

```typescript
interface TestRunResult {
  passed: boolean;
  output: string;
  duration: number;
  summary?: {
    total?: number;
    passed?: number;
    failed?: number;
  };
  validation_errors?: Array<{ line: number; message: string }>;
}

export function useTestCustomRuleContent() {
  return useMutation({
    mutationFn: async (data: { content: string; device_id: number }) => {
      const response = await api.post<TestRunResult>(
        "/rules/custom/test-run/",
        data
      );
      return response.data;
    },
  });
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/use-rules.ts
git commit -m "feat: add useTestCustomRuleContent hook"
```

---

### Task 3: Frontend — Reorganize custom-form.tsx layout

**Files:**
- Modify: `frontend/src/pages/rules/custom-form.tsx`

This is the main UI task. Reorganize from the current two-column (form sidebar + editor) into:

**Row 1 (top, flex-1):** Two side-by-side cards
- Left: Monaco editor card (existing, with validate button)
- Right: Test panel card (new — device selector, test button, result banner, config/output display)

**Row 2 (bottom, auto height):** Single card with form fields in a compact horizontal grid

**Step 1: Add new imports and state**

Add to imports:
```typescript
import { AlertTriangle } from "lucide-react";
import { useFetchDeviceConfig } from "@/hooks/use-devices";
```

Change the import from `use-rules.ts` to also include `useTestCustomRuleContent`.

Add test panel state variables alongside existing state:
```typescript
const testRun = useTestCustomRuleContent();
const [testDeviceId, setTestDeviceId] = useState<number | null>(null);
const [testResult, setTestResult] = useState<TestRunResult | null>(null);
```

Add type import for `TestRunResult` (or inline it).

**Step 2: Add test handler**

```typescript
function handleTestRun() {
  if (!testDeviceId) return;
  setTestResult(null);
  testRun.mutate(
    { content: formData.content, device_id: testDeviceId },
    {
      onSuccess: (data) => setTestResult(data),
    }
  );
}
```

**Step 3: Reorganize the JSX layout**

Replace the current split layout with:

```tsx
{/* Row 1: Editor + Tester */}
<div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
  {/* Left — Editor */}
  <Card className="flex-1 flex flex-col min-h-[400px]">
    <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
      <CardTitle className="text-base font-mono">
        {formData.filename || "test_rule.py"}
      </CardTitle>
      <div className="flex items-center gap-2">
        {/* existing validation status + validate button */}
      </div>
    </CardHeader>
    <CardContent className="flex-1 p-0 overflow-hidden">
      <Editor ... />
    </CardContent>
  </Card>

  {/* Right — Test Rule */}
  <Card className="lg:w-[420px] lg:shrink-0 flex flex-col min-h-[400px]">
    <CardHeader className="pb-2">
      <CardTitle className="text-base">Test Rule</CardTitle>
      <div className="flex items-center gap-2 pt-2">
        <select ... testDeviceId ...>
          <option value="">Select a device...</option>
          {devicesData?.results.map(...)}
        </select>
        <Button onClick={handleTestRun} disabled={!testDeviceId || testRun.isPending}>
          <Play className="mr-1 h-3 w-3" />
          {testRun.isPending ? "Running..." : "Test"}
        </Button>
      </div>
    </CardHeader>
    <CardContent className="flex-1 flex flex-col min-h-0 gap-2">
      {/* Result banner */}
      {testResult && (
        <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-md ${
          testResult.passed
            ? "bg-green-500/10 text-green-500"
            : "bg-red-500/10 text-red-500"
        }`}>
          {testResult.passed
            ? <CheckCircle2 className="h-4 w-4 shrink-0" />
            : <XCircle className="h-4 w-4 shrink-0" />}
          {testResult.passed ? "All tests passed" : "Tests failed"}
          {testResult.duration > 0 && (
            <span className="text-muted-foreground ml-auto">
              {testResult.duration}s
            </span>
          )}
        </div>
      )}
      {/* Output display */}
      {testResult ? (
        <div className="flex-1 overflow-auto rounded-md border bg-muted/30 p-3 font-mono text-sm whitespace-pre-wrap">
          {testResult.output || "No output"}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
          Select a device and click Test to run this rule
        </div>
      )}
    </CardContent>
  </Card>
</div>

{/* Row 2: Form Fields */}
<Card>
  <CardContent className="pt-6">
    <form onSubmit={handleSubmit}>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Name — spans 1 col */}
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" value={formData.name} onChange={...} required />
        </div>
        {/* Description — spans 1 col */}
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Input id="description" value={formData.description} onChange={...} />
        </div>
        {/* Filename */}
        <div className="space-y-2">
          <Label htmlFor="filename">Filename</Label>
          <Input id="filename" value={formData.filename} onChange={...} required />
        </div>
        {/* Severity */}
        <div className="space-y-2">
          <Label htmlFor="severity">Severity</Label>
          <select id="severity" ... />
        </div>
        {/* Device */}
        <div className="space-y-2">
          <Label htmlFor="device">Device</Label>
          <select id="device" ... />
        </div>
        {/* Group */}
        <div className="space-y-2">
          <Label htmlFor="group">Group</Label>
          <select id="group" ... />
        </div>
        {/* Enabled + Buttons */}
        <div className="flex items-end gap-4 col-span-2">
          <div className="flex items-center gap-2 pb-2">
            <Checkbox id="enabled" ... />
            <Label htmlFor="enabled">Enabled</Label>
          </div>
          <div className="flex gap-2 ml-auto">
            <Button type="submit" disabled={...}>
              {isEdit ? "Update Rule" : "Create Rule"}
            </Button>
            <Button variant="outline" asChild>
              <Link to="/rules/custom">Cancel</Link>
            </Button>
          </div>
        </div>
      </div>
    </form>
  </CardContent>
</Card>
```

**Step 4: Verify the page renders**

Start dev server and navigate to `/rules/custom/new`. Verify:
- Top row shows editor on left, test panel on right
- Bottom row shows form fields in a grid
- Validate button still works
- Test button calls the backend endpoint

**Step 5: Commit**

```bash
git add frontend/src/pages/rules/custom-form.tsx
git commit -m "feat: reorganize custom rule form with test panel"
```
