import { Link } from "react-router-dom";
import { Server, ClipboardCheck, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDashboardSummary, useAuditRuns } from "@/hooks/use-audits";
import { StatusBadge, TriggerBadge } from "@/components/badges";

export function DashboardPage() {
  const summary = useDashboardSummary();
  const audits = useAuditRuns({ ordering: "-created_at", page_size: "10" });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
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
              Recent Audits 24h
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
              Pass Rate 7d
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.isLoading
                ? "\u2014"
                : `${Math.round((summary.data?.pass_rate ?? 0) * 100)}%`}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Audits Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Audits</CardTitle>
        </CardHeader>
        <CardContent>
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
                      <Link
                        to={`/audits/${audit.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {audit.device_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={audit.status} />
                    </TableCell>
                    <TableCell>
                      <TriggerBadge trigger={audit.trigger} />
                    </TableCell>
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
        </CardContent>
      </Card>
    </div>
  );
}
