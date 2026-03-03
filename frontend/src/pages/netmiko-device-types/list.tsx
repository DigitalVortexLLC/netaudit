import { Link } from "react-router-dom";
import { Pencil, Plus } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { NetmikoDeviceType } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable } from "@/components/data-table/data-table";
import { DeleteDialog } from "@/components/delete-dialog";
import { useNetmikoDeviceTypes, useDeleteNetmikoDeviceType } from "@/hooks/use-netmiko-device-types";

const columns: ColumnDef<NetmikoDeviceType>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <Link
        to={`/netmiko-device-types/${row.original.id}/edit`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "driver",
    header: "Driver",
  },
  {
    accessorKey: "default_command",
    header: "Default Command",
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => <DeviceTypeActions deviceType={row.original} />,
  },
];

function DeviceTypeActions({ deviceType }: { deviceType: NetmikoDeviceType }) {
  const deleteMutation = useDeleteNetmikoDeviceType();

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" asChild>
        <Link to={`/netmiko-device-types/${deviceType.id}/edit`}>
          <Pencil className="h-4 w-4" />
        </Link>
      </Button>
      <DeleteDialog
        name={deviceType.name}
        onConfirm={() => deleteMutation.mutate(deviceType.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

export function NetmikoDeviceTypeListPage() {
  const { data, isLoading } = useNetmikoDeviceTypes();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Device Types</h1>
        <Button asChild>
          <Link to="/netmiko-device-types/new">
            <Plus className="h-4 w-4" />
            Add Device Type
          </Link>
        </Button>
      </div>

      <Card>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <DataTable columns={columns} data={data?.results ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
