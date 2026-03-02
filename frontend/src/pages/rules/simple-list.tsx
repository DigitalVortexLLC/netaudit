import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { SimpleRule } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable } from "@/components/data-table/data-table";
import { SeverityBadge, EnabledBadge } from "@/components/badges";
import { DeleteDialog } from "@/components/delete-dialog";
import { useSimpleRules, useDeleteSimpleRule } from "@/hooks/use-rules";

export function SimpleRuleListPage() {
  const { data, isLoading } = useSimpleRules();
  const deleteRule = useDeleteSimpleRule();

  const columns: ColumnDef<SimpleRule>[] = [
    {
      accessorKey: "name",
      header: "Name",
    },
    {
      accessorKey: "rule_type",
      header: "Rule Type",
    },
    {
      accessorKey: "pattern",
      header: "Pattern",
      cell: ({ row }) => {
        const pattern = row.original.pattern;
        return pattern.length > 30 ? `${pattern.slice(0, 30)}...` : pattern;
      },
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
            <Link to={`/rules/simple/${row.original.id}/edit`}>Edit</Link>
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
        <h1 className="text-2xl font-bold">Simple Rules</h1>
        <Button asChild>
          <Link to="/rules/simple/new">
            <Plus className="mr-2 h-4 w-4" />
            New Simple Rule
          </Link>
        </Button>
      </div>

      <Card>
        <CardContent>
          <DataTable columns={columns} data={data?.results ?? []} />
        </CardContent>
      </Card>
    </div>
  );
}
