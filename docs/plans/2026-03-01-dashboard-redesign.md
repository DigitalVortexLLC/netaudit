# Dashboard Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the dashboard to show 4 stat cards, a Highcharts compliance trend chart with time range toggles, and a tabbed table with Recent Audits and Recent Issues tabs.

**Architecture:** Backend adds `failed_rule_count_24h` to `/dashboard/summary/`. Frontend installs Highcharts + shadcn tabs, replaces dashboard.tsx with new layout. Chart data computed client-side from completed audit runs.

**Tech Stack:** Django REST Framework, React 18, TypeScript, Highcharts, shadcn/ui, TanStack Query

---

### Task 1: Add `failed_rule_count_24h` to backend dashboard summary

**Files:**
- Modify: `backend/audits/views.py:92-130` (DashboardSummaryView)
- Test: `backend/audits/tests.py` (add DashboardSummaryAPITests)

**Step 1: Write the failing test**

Add to `backend/audits/tests.py`:

```python
class DashboardSummaryAPITests(AuditFixtureMixin, APITestCase):
    """Tests for the dashboard summary endpoint."""

    def setUp(self):
        from users.models import User
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=self.user)

    def test_summary_returns_failed_rule_count(self):
        device = self.create_device()
        run = self.create_audit_run(
            device=device,
            status=AuditRun.Status.COMPLETED,
            summary={"passed": 3, "failed": 2, "error": 0},
        )
        run.completed_at = timezone.now()
        run.save()

        RuleResult.objects.create(
            audit_run=run, test_node_id="t1", outcome="failed",
            message="fail", severity="high",
        )
        RuleResult.objects.create(
            audit_run=run, test_node_id="t2", outcome="failed",
            message="fail", severity="medium",
        )
        RuleResult.objects.create(
            audit_run=run, test_node_id="t3", outcome="passed",
            message="ok", severity="low",
        )

        response = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["failed_rule_count_24h"], 2)

    def test_summary_excludes_old_failures(self):
        device = self.create_device()
        run = self.create_audit_run(
            device=device,
            status=AuditRun.Status.COMPLETED,
            summary={"passed": 0, "failed": 1, "error": 0},
        )
        run.completed_at = timezone.now() - timedelta(hours=25)
        run.save()

        RuleResult.objects.create(
            audit_run=run, test_node_id="t1", outcome="failed",
            message="old fail", severity="high",
        )

        response = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(response.data["failed_rule_count_24h"], 0)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test audits.tests.DashboardSummaryAPITests -v2`
Expected: FAIL — `KeyError: 'failed_rule_count_24h'`

**Step 3: Write minimal implementation**

In `backend/audits/views.py`, add to the `DashboardSummaryView.get` method, after the `pass_rate` calculation and before `return Response(...)`:

```python
        failed_rule_count_24h = RuleResult.objects.filter(
            outcome=RuleResult.Outcome.FAILED,
            audit_run__completed_at__gte=last_24h,
        ).count()
```

Add `RuleResult` to the existing import from `audits.models` at the top of the file. Add `"failed_rule_count_24h": failed_rule_count_24h` to the Response dict.

**Step 4: Run test to verify it passes**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test audits.tests.DashboardSummaryAPITests -v2`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add backend/audits/views.py backend/audits/tests.py
git commit -m "feat: add failed_rule_count_24h to dashboard summary API"
```

---

### Task 2: Install frontend dependencies (Highcharts, tabs)

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/components/ui/tabs.tsx` (via shadcn CLI)

**Step 1: Install Highcharts packages**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npm install highcharts highcharts-react-official
```

**Step 2: Install shadcn tabs component**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npx shadcn@latest add tabs --yes
```

**Step 3: Verify tabs component was created**

Check that `frontend/src/components/ui/tabs.tsx` exists.

**Step 4: Run TypeScript check**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/ui/tabs.tsx
git commit -m "feat: install highcharts and shadcn tabs component"
```

---

### Task 3: Update TypeScript types for dashboard

**Files:**
- Modify: `frontend/src/types/audit.ts:43-47` (DashboardSummary interface)

**Step 1: Add `failed_rule_count_24h` to DashboardSummary**

In `frontend/src/types/audit.ts`, update the `DashboardSummary` interface:

```typescript
export interface DashboardSummary {
  device_count: number;
  recent_audit_count: number;
  pass_rate: number;
  failed_rule_count_24h: number;
}
```

**Step 2: Add `useCompletedAudits` hook for chart data**

In `frontend/src/hooks/use-audits.ts`, add a new hook after `useDashboardSummary`:

```typescript
export function useCompletedAudits(days: number) {
  return useQuery({
    queryKey: ["audits", "completed", days],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<AuditRun>>("/audits/", {
        params: {
          status: "completed",
          ordering: "-completed_at",
          page_size: "500",
        },
      });
      return response.data;
    },
  });
}
```

**Step 3: Add `useRecentIssues` hook for issues tab**

Also in `frontend/src/hooks/use-audits.ts`, add:

```typescript
export function useRecentIssues(count: number = 5) {
  const audits = useAuditRuns({
    status: "completed",
    ordering: "-completed_at",
    page_size: String(count),
  });

  const auditIds = audits.data?.results.map((a) => a.id) ?? [];

  const detailQueries = auditIds.map((id) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useAuditRun(id)
  );

  // NOTE: The above won't work with hooks rules.
  // Instead, fetch details in a single effect. See alternative below.
  return audits;
}
```

Actually, a simpler approach: add a dedicated hook that fetches audit details for the N most recent completed audits, then flattens failed results. Since we can't call hooks in a loop, use a single query that fetches multiple details:

```typescript
export function useRecentIssues() {
  return useQuery({
    queryKey: ["recent-issues"],
    queryFn: async () => {
      // Get 5 most recent completed audits
      const auditsRes = await api.get<PaginatedResponse<AuditRun>>("/audits/", {
        params: { status: "completed", ordering: "-completed_at", page_size: "5" },
      });
      // Fetch details for each (includes results)
      const details = await Promise.all(
        auditsRes.data.results.map((a) =>
          api.get<AuditRunDetail>(`/audits/${a.id}/`).then((r) => r.data)
        )
      );
      // Flatten to failed/error results with audit context
      type IssueRow = RuleResult & { device_name: string; audit_id: number; audit_date: string };
      const issues: IssueRow[] = [];
      for (const audit of details) {
        for (const result of audit.results) {
          if (result.outcome === "failed" || result.outcome === "error") {
            issues.push({
              ...result,
              device_name: audit.device_name,
              audit_id: audit.id,
              audit_date: audit.created_at,
            });
          }
        }
      }
      return issues.slice(0, 20);
    },
  });
}
```

Add the needed type imports at the top: add `AuditRunDetail` and `RuleResult` to the existing import from `@/types`.

**Step 4: Run TypeScript check**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 5: Commit**

```bash
git add frontend/src/types/audit.ts frontend/src/hooks/use-audits.ts
git commit -m "feat: add dashboard types and hooks for chart and issues"
```

---

### Task 4: Create Highcharts compliance chart component

**Files:**
- Create: `frontend/src/components/compliance-chart.tsx`

**Step 1: Create the compliance chart component**

Create `frontend/src/components/compliance-chart.tsx`:

```tsx
import { useState, useMemo } from "react";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useCompletedAudits } from "@/hooks/use-audits";
import type { AuditRun } from "@/types";

type Range = "24h" | "7d" | "30d";

function aggregateByPeriod(audits: AuditRun[], range: Range) {
  const now = new Date();
  const cutoff = new Date(now);
  if (range === "24h") cutoff.setHours(cutoff.getHours() - 24);
  else if (range === "7d") cutoff.setDate(cutoff.getDate() - 7);
  else cutoff.setDate(cutoff.getDate() - 30);

  const filtered = audits.filter(
    (a) => a.completed_at && new Date(a.completed_at) >= cutoff
  );

  // Group by period key
  const buckets = new Map<string, { passed: number; total: number }>();
  for (const audit of filtered) {
    if (!audit.summary || !audit.completed_at) continue;
    const date = new Date(audit.completed_at);
    const key =
      range === "24h"
        ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:00`
        : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

    const existing = buckets.get(key) ?? { passed: 0, total: 0 };
    existing.passed += audit.summary.passed ?? 0;
    existing.total +=
      (audit.summary.passed ?? 0) +
      (audit.summary.failed ?? 0) +
      (audit.summary.error ?? 0);
    buckets.set(key, existing);
  }

  // Sort by key and convert to chart data
  const sorted = [...buckets.entries()].sort(([a], [b]) => a.localeCompare(b));
  return {
    categories: sorted.map(([key]) => key),
    data: sorted.map(([, v]) => (v.total > 0 ? Math.round((v.passed / v.total) * 1000) / 10 : 0)),
    passed: sorted.map(([, v]) => v.passed),
    total: sorted.map(([, v]) => v.total),
  };
}

export function ComplianceChart() {
  const [range, setRange] = useState<Range>("30d");
  const audits = useCompletedAudits(30);

  const chartData = useMemo(() => {
    if (!audits.data?.results) return { categories: [], data: [], passed: [], total: [] };
    return aggregateByPeriod(audits.data.results, range);
  }, [audits.data, range]);

  const options: Highcharts.Options = {
    chart: {
      type: "areaspline",
      backgroundColor: "transparent",
      height: 300,
      style: { fontFamily: "inherit" },
    },
    title: { text: undefined },
    xAxis: {
      categories: chartData.categories,
      labels: { style: { color: "#888" } },
      lineColor: "#3a3a5a",
      tickColor: "#3a3a5a",
    },
    yAxis: {
      title: { text: undefined },
      min: 0,
      max: 100,
      labels: {
        format: "{value}%",
        style: { color: "#888" },
      },
      gridLineColor: "#3a3a5a",
    },
    legend: { enabled: false },
    tooltip: {
      backgroundColor: "#1a1a2e",
      borderColor: "#3a3a5a",
      style: { color: "#e0e0e0" },
      formatter: function (this: Highcharts.TooltipFormatterContextObject) {
        const idx = this.point.index;
        return `<b>${chartData.categories[idx]}</b><br/>Compliance: <b>${this.y}%</b><br/>Passed: ${chartData.passed[idx]} / ${chartData.total[idx]}`;
      },
    },
    plotOptions: {
      areaspline: {
        fillColor: {
          linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [
            [0, "rgba(100, 181, 246, 0.3)"],
            [1, "rgba(100, 181, 246, 0.0)"],
          ],
        },
        lineColor: "#64b5f6",
        lineWidth: 2,
        marker: {
          enabled: false,
          states: { hover: { enabled: true, fillColor: "#64b5f6" } },
        },
      },
    },
    series: [
      {
        type: "areaspline",
        name: "Compliance",
        data: chartData.data,
      },
    ],
    credits: { enabled: false },
  };

  const ranges: { key: Range; label: string }[] = [
    { key: "24h", label: "Last 24h" },
    { key: "7d", label: "Last 7 days" },
    { key: "30d", label: "Last 30 days" },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle>Compliance Trend</CardTitle>
          <p className="text-sm text-muted-foreground">
            Compliance percentage over time
          </p>
        </div>
        <div className="flex gap-1">
          {ranges.map((r) => (
            <Button
              key={r.key}
              variant={range === r.key ? "default" : "outline"}
              size="sm"
              onClick={() => setRange(r.key)}
            >
              {r.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {audits.isLoading ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            Loading chart data...
          </div>
        ) : chartData.categories.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No audit data available for this period.
          </div>
        ) : (
          <HighchartsReact highcharts={Highcharts} options={options} />
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Run TypeScript check**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add frontend/src/components/compliance-chart.tsx
git commit -m "feat: add Highcharts compliance trend chart component"
```

---

### Task 5: Rewrite dashboard page

**Files:**
- Modify: `frontend/src/pages/dashboard.tsx` (full rewrite)

**Step 1: Replace dashboard.tsx with new layout**

Replace the entire contents of `frontend/src/pages/dashboard.tsx`:

```tsx
import { Link } from "react-router-dom";
import { Server, ClipboardCheck, TrendingUp, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDashboardSummary, useAuditRuns, useRecentIssues } from "@/hooks/use-audits";
import { StatusBadge, TriggerBadge, SeverityBadge, OutcomeBadge } from "@/components/badges";
import { ComplianceChart } from "@/components/compliance-chart";

export function DashboardPage() {
  const summary = useDashboardSummary();
  const audits = useAuditRuns({ ordering: "-created_at", page_size: "10" });
  const issues = useRecentIssues();

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* 4 Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Devices
            </CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.isLoading ? "\u2014" : summary.data?.device_count}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Audits (24h)
            </CardTitle>
            <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.isLoading ? "\u2014" : summary.data?.recent_audit_count}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pass Rate (7d)
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.isLoading
                ? "\u2014"
                : `${summary.data?.pass_rate ?? 0}%`}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Failed Rules (24h)
            </CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.isLoading ? "\u2014" : summary.data?.failed_rule_count_24h}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Compliance Chart */}
      <ComplianceChart />

      {/* Tabbed Table */}
      <Card>
        <Tabs defaultValue="audits">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle>Activity</CardTitle>
              <TabsList>
                <TabsTrigger value="audits">Recent Audits</TabsTrigger>
                <TabsTrigger value="issues">Recent Issues</TabsTrigger>
              </TabsList>
            </div>
          </CardHeader>
          <CardContent>
            <TabsContent value="audits" className="mt-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Trigger</TableHead>
                    <TableHead>Summary</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {audits.isLoading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : audits.data?.results.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        No audits found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    audits.data?.results.map((audit) => (
                      <TableRow key={audit.id}>
                        <TableCell>
                          <Link to={`/audits/${audit.id}`} className="font-medium text-primary hover:underline">
                            {audit.device_name}
                          </Link>
                        </TableCell>
                        <TableCell><StatusBadge status={audit.status} /></TableCell>
                        <TableCell><TriggerBadge trigger={audit.trigger} /></TableCell>
                        <TableCell>
                          {audit.summary
                            ? `${audit.summary.passed} passed / ${audit.summary.failed} failed`
                            : "\u2014"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(audit.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="issues" className="mt-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Rule</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Outcome</TableHead>
                    <TableHead>Message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {issues.isLoading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : !issues.data || issues.data.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        No recent issues found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    issues.data.map((issue, idx) => (
                      <TableRow key={`${issue.audit_id}-${issue.id}-${idx}`}>
                        <TableCell>
                          <Link to={`/audits/${issue.audit_id}`} className="font-medium text-primary hover:underline">
                            {issue.device_name}
                          </Link>
                        </TableCell>
                        <TableCell>{issue.rule_name ?? "\u2014"}</TableCell>
                        <TableCell><SeverityBadge severity={issue.severity as "critical" | "high" | "medium" | "low" | "info"} /></TableCell>
                        <TableCell><OutcomeBadge outcome={issue.outcome} /></TableCell>
                        <TableCell className="max-w-[300px] truncate text-muted-foreground" title={issue.message}>
                          {issue.message}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>
    </div>
  );
}
```

**Step 2: Run TypeScript check**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add frontend/src/pages/dashboard.tsx
git commit -m "feat: redesign dashboard with stat cards, chart, and tabbed table"
```

---

### Task 6: Visual verification and polish

**Step 1: Start preview server and verify**

Start the frontend dev server and take a screenshot. Verify:
- 4 stat cards in a row on desktop
- Compliance chart renders with toggle buttons
- Tabbed table switches between Recent Audits and Recent Issues
- Dark theme applied consistently

**Step 2: Fix any TypeScript or visual issues found during verification**

**Step 3: Run production build**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend && npm run build
```

Expected: Build succeeds.

**Step 4: Final commit**

```bash
git add -A
git commit -m "fix: dashboard polish and visual adjustments"
```
