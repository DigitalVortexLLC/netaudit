import { Link } from "react-router-dom";
import { Server, ClipboardCheck, TrendingUp, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDashboardSummary, useAuditRuns, useRecentIssues } from "@/hooks/use-audits";
import type { Severity } from "@/types";
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
                        <TableCell><SeverityBadge severity={issue.severity as Severity} /></TableCell>
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
