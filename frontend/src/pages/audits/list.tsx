import { Link } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import type { AuditRun } from "@/types";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge, TriggerBadge } from "@/components/badges";
import { useAuditRuns } from "@/hooks/use-audits";

const columns: ColumnDef<AuditRun>[] = [
  {
    accessorKey: "device_name",
    header: "Device",
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
    header: "Status",
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "trigger",
    header: "Trigger",
    cell: ({ row }) => <TriggerBadge trigger={row.original.trigger} />,
  },
  {
    id: "summary",
    header: "Summary",
    cell: ({ row }) => {
      const summary = row.original.summary;
      return summary ? `${summary.passed}P / ${summary.failed}F` : "\u2014";
    },
  },
  {
    accessorKey: "created_at",
    header: "Date",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {new Date(row.original.created_at).toLocaleString()}
      </span>
    ),
  },
];

export function AuditListPage() {
  const { data, isLoading } = useAuditRuns();

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Audits</h1>

      {isLoading ? (
        <div className="text-center text-muted-foreground py-8">Loading...</div>
      ) : (
        <DataTable columns={columns} data={data?.results ?? []} />
      )}
    </div>
  );
}
