import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Server, FolderTree, Shield, Code,
  ClipboardCheck, Clock, Settings, Users, LogOut, UserCircle,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  exact?: boolean;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, exact: true },
  { label: "Devices", href: "/devices", icon: Server },
  { label: "Groups", href: "/groups", icon: FolderTree },
  { label: "Simple Rules", href: "/rules/simple", icon: Shield },
  { label: "Custom Rules", href: "/rules/custom", icon: Code },
  { label: "Audits", href: "/audits", icon: ClipboardCheck },
  { label: "Schedules", href: "/schedules", icon: Clock },
  { label: "Settings", href: "/settings", icon: Settings },
];

const adminItems: NavItem[] = [
  { label: "Users", href: "/users", icon: Users },
];

function isActive(pathname: string, href: string, exact?: boolean): boolean {
  if (exact) return pathname === href;
  return pathname.startsWith(href);
}

const roleBadgeVariant = (role: string) => {
  switch (role) {
    case "admin": return "destructive" as const;
    case "editor": return "default" as const;
    default: return "secondary" as const;
  }
};

export function AppSidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();

  const allItems = user?.role === "admin"
    ? [...navItems, ...adminItems]
    : navItems;

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-56 flex-col bg-sidebar border-r border-sidebar-border">
      {/* Header */}
      <div className="flex h-14 items-center border-b border-sidebar-border px-5">
        <Link to="/" className="text-lg font-semibold text-white hover:no-underline">
          Netaudit
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2">
        <ul className="space-y-0.5 px-2">
          {allItems.map((item) => {
            const active = isActive(location.pathname, item.href, item.exact);
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors no-underline",
                    active
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User footer */}
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-white truncate">
            {user?.username}
          </span>
          <Badge variant={roleBadgeVariant(user?.role || "viewer")} className="text-xs">
            {user?.role}
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/profile"
            className="text-xs text-sidebar-foreground hover:text-white no-underline flex items-center gap-1"
          >
            <UserCircle className="h-3 w-3" />
            Profile
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="h-auto p-0 text-xs text-sidebar-foreground hover:text-white"
          >
            <LogOut className="h-3 w-3 mr-1" />
            Logout
          </Button>
        </div>
      </div>
    </aside>
  );
}
