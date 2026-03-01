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

  const sorted = [...buckets.entries()].sort(([a], [b]) => a.localeCompare(b));
  return {
    categories: sorted.map(([key]) => key),
    data: sorted.map(([, v]) =>
      v.total > 0 ? Math.round((v.passed / v.total) * 1000) / 10 : 0
    ),
    passed: sorted.map(([, v]) => v.passed),
    total: sorted.map(([, v]) => v.total),
  };
}

export function ComplianceChart() {
  const [range, setRange] = useState<Range>("30d");
  const audits = useCompletedAudits(30);

  const chartData = useMemo(() => {
    if (!audits.data?.results)
      return { categories: [], data: [], passed: [], total: [] };
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
      formatter() {
        const idx = (this as unknown as { point: { index: number } }).point.index;
        const y = (this as unknown as { y: number }).y;
        return `<b>${chartData.categories[idx]}</b><br/>Compliance: <b>${y}%</b><br/>Passed: ${chartData.passed[idx]} / ${chartData.total[idx]}`;
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
