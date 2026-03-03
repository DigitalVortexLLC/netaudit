import { Link } from "react-router-dom";
import { Pencil } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { User } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, SortableHeader } from "@/components/data-table/data-table";
import { EnabledBadge } from "@/components/badges";
import { useUsers } from "@/hooks/use-users";
import { useAuth } from "@/hooks/use-auth";

const columns: ColumnDef<User>[] = [
  {
    accessorKey: "username",
    header: ({ column }) => <SortableHeader column={column}>Username</SortableHeader>,
  },
  {
    accessorKey: "email",
    header: ({ column }) => <SortableHeader column={column}>Email</SortableHeader>,
  },
  {
    accessorKey: "role",
    header: ({ column }) => <SortableHeader column={column}>Role</SortableHeader>,
    cell: ({ row }) => (
      <Badge variant="secondary">{row.original.role}</Badge>
    ),
  },
  {
    accessorKey: "is_api_enabled",
    header: ({ column }) => <SortableHeader column={column}>API Enabled</SortableHeader>,
    cell: ({ row }) => <EnabledBadge enabled={row.original.is_api_enabled} />,
  },
  {
    accessorKey: "date_joined",
    header: ({ column }) => <SortableHeader column={column}>Joined</SortableHeader>,
    cell: ({ row }) =>
      new Date(row.original.date_joined).toLocaleDateString(),
  },
  {
    id: "actions",
    header: "Actions",
    enableGlobalFilter: false,
    cell: ({ row }) => (
      <Button variant="outline" size="sm" asChild>
        <Link to={`/users/${row.original.id}/edit`}>
          <Pencil className="h-4 w-4" />
        </Link>
      </Button>
    ),
  },
];

export function UserListPage() {
  const { user } = useAuth();
  const { data, isLoading } = useUsers();

  if (user?.role !== "admin") {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground mt-2">
          You do not have permission to view this page.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Users</h1>

      <Card>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <DataTable columns={columns} data={data?.results ?? []} searchPlaceholder="Search users..." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
