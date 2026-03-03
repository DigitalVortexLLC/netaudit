import { Link } from "react-router-dom";
import { Pencil, Plus } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Device } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, SortableHeader } from "@/components/data-table/data-table";
import { EnabledBadge } from "@/components/badges";
import { DeleteDialog } from "@/components/delete-dialog";
import { useDevices, useDeleteDevice } from "@/hooks/use-devices";

const columns: ColumnDef<Device>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => <SortableHeader column={column}>Name</SortableHeader>,
    cell: ({ row }) => (
      <Link
        to={`/devices/${row.original.id}`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "hostname",
    header: ({ column }) => <SortableHeader column={column}>Hostname</SortableHeader>,
  },
  {
    accessorKey: "enabled",
    header: ({ column }) => <SortableHeader column={column}>Enabled</SortableHeader>,
    cell: ({ row }) => <EnabledBadge enabled={row.original.enabled} />,
  },
  {
    id: "actions",
    header: "Actions",
    enableGlobalFilter: false,
    cell: ({ row }) => <DeviceActions device={row.original} />,
  },
];

function DeviceActions({ device }: { device: Device }) {
  const deleteMutation = useDeleteDevice();

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" asChild>
        <Link to={`/devices/${device.id}/edit`}>
          <Pencil className="h-4 w-4" />
        </Link>
      </Button>
      <DeleteDialog
        name={device.name}
        onConfirm={() => deleteMutation.mutate(device.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

export function DeviceListPage() {
  const { data, isLoading } = useDevices();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Devices</h1>
        <Button asChild>
          <Link to="/devices/new">
            <Plus className="h-4 w-4" />
            Add Device
          </Link>
        </Button>
      </div>

      <Card>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <DataTable columns={columns} data={data?.results ?? []} searchPlaceholder="Search devices..." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
