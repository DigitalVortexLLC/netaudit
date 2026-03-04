import { Link } from "react-router-dom";
import { Plus, Pencil } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { DeviceGroup } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, SortableHeader } from "@/components/data-table/data-table";
import { DeleteDialog } from "@/components/delete-dialog";
import { useGroups, useDeleteGroup } from "@/hooks/use-groups";

const columns: ColumnDef<DeviceGroup>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => <SortableHeader column={column}>Name</SortableHeader>,
    cell: ({ row }) => (
      <Link
        to={`/groups/${row.original.id}`}
        className="font-medium text-primary hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "description",
    header: ({ column }) => <SortableHeader column={column}>Description</SortableHeader>,
    cell: ({ row }) => {
      const desc = row.original.description;
      return desc && desc.length > 50 ? `${desc.slice(0, 50)}...` : desc || "\u2014";
    },
  },
  {
    accessorKey: "device_count",
    header: ({ column }) => <SortableHeader column={column}>Device Count</SortableHeader>,
  },
  {
    id: "actions",
    header: "Actions",
    enableGlobalFilter: false,
    cell: function ActionsCell({ row }) {
      const deleteGroup = useDeleteGroup();
      return (
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/groups/${row.original.id}/edit`}>
              <Pencil className="h-4 w-4" />
            </Link>
          </Button>
          <DeleteDialog
            name={row.original.name}
            onConfirm={() => deleteGroup.mutate(row.original.id)}
            loading={deleteGroup.isPending}
          />
        </div>
      );
    },
  },
];

export function GroupListPage() {
  const { data, isLoading } = useGroups();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Groups</h1>
        <Button asChild>
          <Link to="/groups/new">
            <Plus className="h-4 w-4" />
            Add Group
          </Link>
        </Button>
      </div>

      <Card>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : (
            <DataTable
              columns={columns}
              data={data?.results ?? []}
              pageCount={data ? Math.ceil(data.count / 25) : 1}
              totalCount={data?.count}
              searchPlaceholder="Search groups..."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
