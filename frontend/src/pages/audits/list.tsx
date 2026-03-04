import { useState } from "react";
import { Link } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import type { AuditRun } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable, SortableHeader } from "@/components/data-table/data-table";
import { StatusBadge, TriggerBadge } from "@/components/badges";
import { TagBadge } from "@/components/tag-badge";
import { useAuditRuns } from "@/hooks/use-audits";
import { useTags } from "@/hooks/use-tags";

const columns: ColumnDef<AuditRun>[] = [
  {
    accessorKey: "device_name",
    header: ({ column }) => <SortableHeader column={column}>Device</SortableHeader>,
    cell: ({ row }) => (
      <Link
        to={`/audits/${row.original.id}`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.device_name}
      </Link>
    ),
  },
  {
    accessorKey: "status",
    header: ({ column }) => <SortableHeader column={column}>Status</SortableHeader>,
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "trigger",
    header: ({ column }) => <SortableHeader column={column}>Trigger</SortableHeader>,
    cell: ({ row }) => <TriggerBadge trigger={row.original.trigger} />,
  },
  {
    id: "tags",
    header: "Tags",
    enableGlobalFilter: false,
    cell: ({ row }) => (
      <div className="flex flex-wrap gap-1">
        {row.original.tags?.map((tag) => (
          <TagBadge key={tag.id} name={tag.name} className="text-[10px] px-1.5 py-0" />
        ))}
      </div>
    ),
  },
  {
    id: "summary",
    header: "Summary",
    enableGlobalFilter: false,
    cell: ({ row }) => {
      const summary = row.original.summary;
      return summary ? `${summary.passed}P / ${summary.failed}F` : "\u2014";
    },
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => <SortableHeader column={column}>Date</SortableHeader>,
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {new Date(row.original.created_at).toLocaleString()}
      </span>
    ),
  },
];

export function AuditListPage() {
  const [tagFilter, setTagFilter] = useState<string>("");
  const { data: allTags = [] } = useTags();
  const params: Record<string, string> = {};
  if (tagFilter) params.tags = tagFilter;
  const { data, isLoading } = useAuditRuns(params);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Audits</h1>

      <div className="flex gap-2">
        <Select value={tagFilter || "all"} onValueChange={(v) => setTagFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by tag" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tags</SelectItem>
            {allTags.map((tag) => (
              <SelectItem key={tag.id} value={String(tag.id)}>
                {tag.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <DataTable columns={columns} data={data?.results ?? []} searchPlaceholder="Search audits..." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
