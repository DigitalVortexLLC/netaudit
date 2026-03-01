import { Link } from "react-router-dom";
import { Pencil, Plus } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { AuditSchedule } from "@/types";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table/data-table";
import { EnabledBadge } from "@/components/badges";
import { DeleteDialog } from "@/components/delete-dialog";
import { useSchedules, useDeleteSchedule } from "@/hooks/use-schedules";

const columns: ColumnDef<AuditSchedule>[] = [
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "device",
    header: "Device",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.device}</span>
    ),
  },
  {
    accessorKey: "cron_expression",
    header: "Cron Expression",
    cell: ({ row }) => (
      <code className="font-mono text-sm">{row.original.cron_expression}</code>
    ),
  },
  {
    accessorKey: "enabled",
    header: "Enabled",
    cell: ({ row }) => <EnabledBadge enabled={row.original.enabled} />,
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => <ScheduleActions schedule={row.original} />,
  },
];

function ScheduleActions({ schedule }: { schedule: AuditSchedule }) {
  const deleteMutation = useDeleteSchedule();

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" asChild>
        <Link to={`/schedules/${schedule.id}/edit`}>
          <Pencil className="h-4 w-4" />
        </Link>
      </Button>
      <DeleteDialog
        name={schedule.name}
        onConfirm={() => deleteMutation.mutate(schedule.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

export function ScheduleListPage() {
  const { data, isLoading } = useSchedules();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Schedules</h1>
        <Button asChild>
          <Link to="/schedules/new">
            <Plus className="h-4 w-4" />
            Add Schedule
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground py-8">Loading...</div>
      ) : (
        <DataTable columns={columns} data={data?.results ?? []} />
      )}
    </div>
  );
}
