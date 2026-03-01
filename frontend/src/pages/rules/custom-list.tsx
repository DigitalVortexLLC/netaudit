import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { CustomRule } from "@/types";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table/data-table";
import { SeverityBadge, EnabledBadge } from "@/components/badges";
import { DeleteDialog } from "@/components/delete-dialog";
import { useCustomRules, useDeleteCustomRule } from "@/hooks/use-rules";

export function CustomRuleListPage() {
  const { data, isLoading } = useCustomRules();
  const deleteRule = useDeleteCustomRule();

  const columns: ColumnDef<CustomRule>[] = [
    {
      accessorKey: "name",
      header: "Name",
    },
    {
      accessorKey: "filename",
      header: "Filename",
    },
    {
      accessorKey: "severity",
      header: "Severity",
      cell: ({ row }) => <SeverityBadge severity={row.original.severity} />,
    },
    {
      accessorKey: "enabled",
      header: "Enabled",
      cell: ({ row }) => <EnabledBadge enabled={row.original.enabled} />,
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/rules/custom/${row.original.id}/edit`}>Edit</Link>
          </Button>
          <DeleteDialog
            name={row.original.name}
            onConfirm={() => deleteRule.mutate(row.original.id)}
            loading={deleteRule.isPending}
          />
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Custom Rules</h1>
        <Button asChild>
          <Link to="/rules/custom/new">
            <Plus className="mr-2 h-4 w-4" />
            New Custom Rule
          </Link>
        </Button>
      </div>

      <DataTable columns={columns} data={data?.results ?? []} />
    </div>
  );
}
