import { Outlet } from "react-router-dom";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";
import { CommandPalette } from "@/components/layout/command-palette";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />
      <div className="pl-56">
        <AppHeader />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
