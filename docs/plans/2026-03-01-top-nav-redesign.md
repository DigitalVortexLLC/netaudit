# Top Navigation Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the fixed left sidebar with a top navigation bar using pill/bubble buttons with hover dropdowns.

**Architecture:** Rewrite app-layout.tsx to remove sidebar and use full-width content. Rewrite app-header.tsx to become the top nav bar with logo, nav pills (with hover dropdowns for grouped items), and right-side controls (search, settings gear, user avatar dropdown). Delete app-sidebar.tsx.

**Tech Stack:** React, React Router, Tailwind CSS, Lucide icons, ShadCN DropdownMenu

---

### Task 1: Rewrite app-header.tsx as the Top Nav Bar

**Files:**
- Rewrite: `frontend/src/components/layout/app-header.tsx`

**Step 1: Replace app-header.tsx with the new top nav bar**

Replace the entire contents of `frontend/src/components/layout/app-header.tsx` with:

```tsx
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Server, FolderTree, Shield, Code,
  ClipboardCheck, Clock, Settings, LogOut, UserCircle, Search, ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

interface NavChild {
  label: string;
  href: string;
  icon: typeof Server;
}

interface NavGroup {
  label: string;
  children: NavChild[];
  prefixes: string[];
}

interface NavDirect {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  exact?: boolean;
}

type NavItem = NavDirect | NavGroup;

function isGroup(item: NavItem): item is NavGroup {
  return "children" in item;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, exact: true },
  {
    label: "Netbox",
    prefixes: ["/devices", "/groups"],
    children: [
      { label: "Devices", href: "/devices", icon: Server },
      { label: "Groups", href: "/groups", icon: FolderTree },
    ],
  },
  {
    label: "Rules",
    prefixes: ["/rules"],
    children: [
      { label: "Simple Rules", href: "/rules/simple", icon: Shield },
      { label: "Custom Rules", href: "/rules/custom", icon: Code },
    ],
  },
  {
    label: "Auditing",
    prefixes: ["/audits", "/schedules"],
    children: [
      { label: "Audits", href: "/audits", icon: ClipboardCheck },
      { label: "Schedules", href: "/schedules", icon: Clock },
    ],
  },
];

function isDirectActive(pathname: string, item: NavDirect): boolean {
  if (item.exact) return pathname === item.href;
  return pathname.startsWith(item.href);
}

function isGroupActive(pathname: string, item: NavGroup): boolean {
  return item.prefixes.some((p) => pathname.startsWith(p));
}

const roleBadgeVariant = (role: string) => {
  switch (role) {
    case "admin": return "destructive" as const;
    case "editor": return "default" as const;
    default: return "secondary" as const;
  }
};

function NavPillDirect({ item }: { item: NavDirect }) {
  const location = useLocation();
  const active = isDirectActive(location.pathname, item);

  return (
    <Link
      to={item.href}
      className={cn(
        "flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium transition-colors no-underline",
        active
          ? "bg-primary text-primary-foreground"
          : "text-[#b0b0c8] hover:bg-[#2a2a4a] hover:text-white"
      )}
    >
      <item.icon className="h-4 w-4" />
      {item.label}
    </Link>
  );
}

function NavPillGroup({ item }: { item: NavGroup }) {
  const location = useLocation();
  const active = isGroupActive(location.pathname, item);
  const [open, setOpen] = useState(false);
  const [timeoutId, setTimeoutId] = useState<ReturnType<typeof setTimeout> | null>(null);

  const handleEnter = () => {
    if (timeoutId) clearTimeout(timeoutId);
    setOpen(true);
  };

  const handleLeave = () => {
    const id = setTimeout(() => setOpen(false), 150);
    setTimeoutId(id);
  };

  return (
    <div
      className="relative"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <button
        className={cn(
          "flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
          active || open
            ? "bg-primary text-primary-foreground"
            : "text-[#b0b0c8] hover:bg-[#2a2a4a] hover:text-white"
        )}
      >
        {item.label}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 min-w-[180px] rounded-lg border border-border bg-card p-1 shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
          {item.children.map((child) => {
            const childActive = location.pathname.startsWith(child.href);
            return (
              <Link
                key={child.href}
                to={child.href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm no-underline transition-colors",
                  childActive
                    ? "bg-primary/10 text-primary"
                    : "text-card-foreground hover:bg-accent hover:text-accent-foreground"
                )}
                onClick={() => setOpen(false)}
              >
                <child.icon className="h-4 w-4" />
                {child.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-50 flex h-14 items-center border-b border-border bg-[#1a1a2e] px-6">
      {/* Logo */}
      <Link to="/" className="mr-8 text-lg font-semibold text-white no-underline hover:no-underline">
        Netaudit
      </Link>

      {/* Nav pills */}
      <nav className="flex items-center gap-1">
        {navItems.map((item) =>
          isGroup(item) ? (
            <NavPillGroup key={item.label} item={item} />
          ) : (
            <NavPillDirect key={item.href} item={item} />
          )
        )}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right controls */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <Button
          variant="ghost"
          size="sm"
          className="gap-2 text-[#b0b0c8] hover:text-white hover:bg-[#2a2a4a]"
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
          }}
        >
          <Search className="h-4 w-4" />
          <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border border-[#3a3a5a] bg-[#2a2a4a] px-1.5 font-mono text-[10px] font-medium text-[#b0b0c8] sm:flex">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>

        {/* Settings gear */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-[#b0b0c8] hover:text-white hover:bg-[#2a2a4a]"
          asChild
        >
          <Link to="/settings">
            <Settings className="h-4 w-4" />
          </Link>
        </Button>

        {/* User avatar dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                  {user?.username?.charAt(0).toUpperCase() || "U"}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel className="flex items-center gap-2">
              {user?.username}
              <Badge variant={roleBadgeVariant(user?.role || "viewer")} className="text-xs">
                {user?.role}
              </Badge>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/profile" className="no-underline">
                <UserCircle className="mr-2 h-4 w-4" />
                Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={logout}>
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
```

**Step 2: Verify the file compiles**

Run: `cd /Users/aaronroth/Documents/netaudit && npx tsc --noEmit --project frontend/tsconfig.app.json 2>&1 | head -20`
Expected: No errors related to app-header.tsx

---

### Task 2: Update app-layout.tsx to Remove Sidebar

**Files:**
- Rewrite: `frontend/src/components/layout/app-layout.tsx`

**Step 1: Replace app-layout.tsx**

Replace the entire contents of `frontend/src/components/layout/app-layout.tsx` with:

```tsx
import { Outlet } from "react-router-dom";
import { AppHeader } from "@/components/layout/app-header";
import { CommandPalette } from "@/components/layout/command-palette";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main>
        <Outlet />
      </main>
      <CommandPalette />
    </div>
  );
}
```

Note: Removed AppSidebar import, removed `pl-56` offset, removed `p-6` from main (pages already have their own `p-6`).

**Step 2: Verify the file compiles**

Run: `cd /Users/aaronroth/Documents/netaudit && npx tsc --noEmit --project frontend/tsconfig.app.json 2>&1 | head -20`
Expected: No errors related to app-layout.tsx (may see warning about unused app-sidebar.tsx, that's fine)

---

### Task 3: Delete app-sidebar.tsx

**Files:**
- Delete: `frontend/src/components/layout/app-sidebar.tsx`

**Step 1: Delete the sidebar file**

Run: `rm /Users/aaronroth/Documents/netaudit/frontend/src/components/layout/app-sidebar.tsx`

**Step 2: Verify no remaining imports**

Run: `grep -r "app-sidebar" /Users/aaronroth/Documents/netaudit/frontend/src/`
Expected: No results (the import was already removed in Task 2)

**Step 3: Verify full build compiles**

Run: `cd /Users/aaronroth/Documents/netaudit && npx tsc --noEmit --project frontend/tsconfig.app.json 2>&1 | head -20`
Expected: No errors

---

### Task 4: Visual Verification

**Step 1: Check the dev server is running and reload**

Navigate to `http://localhost:5173/` and take a screenshot.
Expected: Top nav bar with Netaudit logo, Dashboard/Netbox/Rules/Auditing pills, search/settings/avatar on right. Full-width content. No sidebar.

**Step 2: Verify hover dropdowns work**

Hover over the "Netbox" pill.
Expected: Dropdown appears with Devices and Groups items with icons.

**Step 3: Verify navigation works**

Click Devices in the Netbox dropdown.
Expected: Navigates to /devices page. The Netbox pill should be highlighted.

**Step 4: Verify user dropdown works**

Click the avatar.
Expected: Dropdown with username, role badge, Profile link, Logout button.

**Step 5: Verify command palette still works**

Press Cmd+K.
Expected: Command palette opens normally.

---

### Task 5: Commit

**Step 1: Commit all changes**

```bash
git add frontend/src/components/layout/app-header.tsx frontend/src/components/layout/app-layout.tsx
git rm frontend/src/components/layout/app-sidebar.tsx
git commit -m "feat: replace sidebar with top nav bar using pill buttons and hover dropdowns"
```
