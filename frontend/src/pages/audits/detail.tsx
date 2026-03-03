import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OutcomeBadge, SeverityBadge, StatusBadge, TriggerBadge } from "@/components/badges";
import { TagBadge } from "@/components/tag-badge";
import { TagSelector } from "@/components/tag-selector";
import { CommentSection } from "@/components/comment-section";
import { useAuditRun, useAuditConfig } from "@/hooks/use-audits";
import { useAuditWebSocket } from "@/hooks/use-websocket";
import { useTags, useAddAuditTag, useRemoveAuditTag } from "@/hooks/use-tags";
import type { Severity } from "@/types";

export function AuditDetailPage() {
  const { id } = useParams();
  const auditId = Number(id);
  useAuditWebSocket(auditId);
  const { data: audit, isLoading } = useAuditRun(auditId);
  const { data: configData } = useAuditConfig(Number(id));
  const { data: allTags = [] } = useTags();
  const addTag = useAddAuditTag(Number(id));
  const removeTag = useRemoveAuditTag(Number(id));
  const [showConfig, setShowConfig] = useState(false);

  if (isLoading) {
    return (
      <div className="p-6 text-center text-muted-foreground py-8">Loading...</div>
    );
  }

  if (!audit) {
    return (
      <div className="p-6 text-center text-muted-foreground py-8">Audit not found.</div>
    );
  }

  const isInProgress = audit.status === "pending" || audit.status === "fetching_config" || audit.status === "running_rules";

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/audits">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Audit #{id}</h1>
            <p className="text-muted-foreground">{audit.device_name}</p>
          </div>
        </div>
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <p className="text-sm text-muted-foreground">Device</p>
              <Link
                to={`/devices/${audit.device}`}
                className="font-medium text-primary hover:underline"
              >
                {audit.device_name}
              </Link>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <div className="flex items-center gap-2 mt-1">
                <StatusBadge status={audit.status} />
                {isInProgress && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Trigger</p>
              <div className="mt-1">
                <TriggerBadge trigger={audit.trigger} />
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Started</p>
              <p className="font-medium">
                {audit.started_at ? new Date(audit.started_at).toLocaleString() : "\u2014"}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="font-medium">
                {audit.completed_at ? new Date(audit.completed_at).toLocaleString() : "\u2014"}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Summary</p>
              <p className="font-medium">
                {audit.summary
                  ? `${audit.summary.passed} passed / ${audit.summary.failed} failed / ${audit.summary.error} errors`
                  : "\u2014"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tags */}
      <Card>
        <CardHeader>
          <CardTitle>Tags</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2">
            {audit.tags?.map((tag) => (
              <TagBadge
                key={tag.id}
                name={tag.name}
                onRemove={() => removeTag.mutate(tag.id)}
              />
            ))}
            <TagSelector
              allTags={allTags}
              selectedTagIds={audit.tags?.map((t) => t.id) ?? []}
              onAddTag={(data) => addTag.mutate(data)}
              isPending={addTag.isPending}
            />
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {audit.status === "failed" && audit.error_message && (
        <Card className="border-red-800">
          <CardHeader>
            <CardTitle className="text-red-400">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-300">{audit.error_message}</p>
          </CardContent>
        </Card>
      )}

      {/* Results Table */}
      {audit.results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule Name</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {audit.results.map((result) => (
                  <TableRow key={result.id}>
                    <TableCell className="font-medium">
                      {result.rule_name ?? "\u2014"}
                    </TableCell>
                    <TableCell>
                      <OutcomeBadge outcome={result.outcome} />
                    </TableCell>
                    <TableCell>
                      <SeverityBadge severity={result.severity as Severity} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {result.duration != null ? `${result.duration}ms` : "\u2014"}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {result.message || "\u2014"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Comments */}
      <CommentSection auditId={Number(id)} />

      {/* Config Snapshot */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Config Snapshot</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowConfig(!showConfig)}
            >
              {showConfig ? "Hide" : "Show"}
            </Button>
          </div>
        </CardHeader>
        {showConfig && (
          <CardContent>
            <pre className="rounded-md bg-muted p-4 text-sm font-mono overflow-auto max-h-96">
              {configData
                ? JSON.stringify(configData, null, 2)
                : "No config data available."}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
