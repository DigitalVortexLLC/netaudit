# Dashboard Redesign Design

## Overview

Redesign the dashboard to match the shadcn example dashboard pattern: four stat cards, a compliance trend chart, and a tabbed issues table.

## Stat Cards (4-column grid)

| Card | Metric | Source | Icon |
|------|--------|--------|------|
| Total Devices | `device_count` | `/dashboard/summary/` | Server |
| Recent Audits 24h | `recent_audit_count` | `/dashboard/summary/` | ClipboardCheck |
| Pass Rate 7d | `pass_rate` | `/dashboard/summary/` | TrendingUp |
| Failed Rules 24h | `failed_rule_count_24h` | `/dashboard/summary/` (new field) | AlertTriangle |

## Compliance Chart

- **Library**: Highcharts (`highcharts` + `highcharts-react-official`)
- **Type**: Area/spline chart
- **Y-axis**: 0-100% compliance rate
- **X-axis**: Date labels
- **Data source**: Completed audit runs — `passed / (passed + failed) * 100` per day/hour
- **Toggle buttons**: Last 24h | Last 7 days | Last 30 days (default: Last 30 days)
- **Dark theme**: Chart bg matches card bg (`#2d2d2d`), gridlines `#3a3a5a`, area fill `#64b5f6` at 20% opacity
- **Tooltip**: Date, compliance %, passed/failed counts
- **Data fetching**: `GET /audits/?status=completed&ordering=-completed_at&page_size=500` — aggregate client-side by day (or hour for 24h view)

## Tabbed Issues Table

Card with two tabs:

### Tab 1: Recent Audits
- Columns: Device (link to `/audits/{id}`), Status (badge), Trigger (badge), Summary (passed/failed), Date
- 10 most recent audit runs, sorted by `created_at` desc
- Uses existing `useAuditRuns` hook

### Tab 2: Recent Issues
- Columns: Device (link to `/audits/{audit_id}`), Rule Name, Severity (badge), Outcome (badge), Message (truncated)
- Failed/error rule results from recent completed audits
- Fetches last 5 completed audit details, flattens failed results
- Sorted by most recent, limited to 20 rows

## Backend Changes

### `DashboardSummaryView` (audits/views.py)

Add `failed_rule_count_24h`:
- Count `RuleResult` objects where `outcome="failed"` from `AuditRun` objects completed in last 24 hours

### `DashboardSummary` TypeScript type

Add `failed_rule_count_24h: number` field.

## Dependencies

- `highcharts` — charting library
- `highcharts-react-official` — React wrapper for Highcharts
- shadcn `tabs` component (install via `npx shadcn@latest add tabs`)
