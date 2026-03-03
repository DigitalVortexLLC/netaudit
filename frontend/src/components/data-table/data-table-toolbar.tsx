import { type Table } from "@tanstack/react-table";
import { Search, Download, FileSpreadsheet, FileJson } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface DataTableToolbarProps<TData> {
  table: Table<TData>;
  globalFilter: string;
  onGlobalFilterChange: (value: string) => void;
  searchPlaceholder?: string;
}

function escapeCsvField(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function getCellValue(cell: { getValue: () => unknown }): string {
  const value = cell.getValue();
  if (value == null) return "";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function downloadFile(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function DataTableToolbar<TData>({
  table,
  globalFilter,
  onGlobalFilterChange,
  searchPlaceholder = "Search...",
}: DataTableToolbarProps<TData>) {
  const exportCsv = () => {
    const headers = table
      .getAllColumns()
      .filter((col) => col.id !== "actions" && col.getIsVisible())
      .map((col) => {
        const header = col.columnDef.header;
        return typeof header === "string" ? header : col.id;
      });

    const rows = table.getFilteredRowModel().rows.map((row) =>
      row
        .getAllCells()
        .filter(
          (cell) =>
            cell.column.id !== "actions" && cell.column.getIsVisible()
        )
        .map((cell) => escapeCsvField(getCellValue(cell)))
    );

    const csv = [headers.map(escapeCsvField).join(","), ...rows.map((r) => r.join(","))].join("\n");
    downloadFile(csv, "export.csv", "text/csv;charset=utf-8;");
  };

  const exportJson = () => {
    const columns = table
      .getAllColumns()
      .filter((col) => col.id !== "actions" && col.getIsVisible());

    const data = table.getFilteredRowModel().rows.map((row) => {
      const obj: Record<string, string> = {};
      row
        .getAllCells()
        .filter(
          (cell) =>
            cell.column.id !== "actions" && cell.column.getIsVisible()
        )
        .forEach((cell, i) => {
          const header = columns[i]?.columnDef.header;
          const key = typeof header === "string" ? header : cell.column.id;
          obj[key] = getCellValue(cell);
        });
      return obj;
    });

    downloadFile(JSON.stringify(data, null, 2), "export.json", "application/json");
  };

  return (
    <div className="flex items-center justify-between gap-2 pb-4">
      <div className="relative flex-1 max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={searchPlaceholder}
          value={globalFilter}
          onChange={(e) => onGlobalFilterChange(e.target.value)}
          className="pl-8"
        />
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={exportCsv}>
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            Export CSV
          </DropdownMenuItem>
          <DropdownMenuItem onClick={exportJson}>
            <FileJson className="mr-2 h-4 w-4" />
            Export JSON
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
