import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Server, FolderTree, Shield, Code,
  ClipboardCheck, Clock, Settings, Users, UserCircle,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useAuth } from "@/hooks/use-auth";

const pages = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Devices", href: "/devices", icon: Server },
  { label: "Groups", href: "/groups", icon: FolderTree },
  { label: "Simple Rules", href: "/rules/simple", icon: Shield },
  { label: "Custom Rules", href: "/rules/custom", icon: Code },
  { label: "Audits", href: "/audits", icon: ClipboardCheck },
  { label: "Schedules", href: "/schedules", icon: Clock },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Profile", href: "/profile", icon: UserCircle },
];

const adminPages = [
  { label: "Users", href: "/users", icon: Users },
];

const actions = [
  { label: "Add Device", href: "/devices/new", icon: Server },
  { label: "Add Group", href: "/groups/new", icon: FolderTree },
  { label: "Add Simple Rule", href: "/rules/simple/new", icon: Shield },
  { label: "Add Custom Rule", href: "/rules/custom/new", icon: Code },
  { label: "Add Schedule", href: "/schedules/new", icon: Clock },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (href: string) => {
    setOpen(false);
    navigate(href);
  };

  const allPages = user?.role === "admin" ? [...pages, ...adminPages] : pages;

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Pages">
          {allPages.map((page) => (
            <CommandItem key={page.href} onSelect={() => runCommand(page.href)}>
              <page.icon className="mr-2 h-4 w-4" />
              {page.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          {actions.map((action) => (
            <CommandItem key={action.href} onSelect={() => runCommand(action.href)}>
              <action.icon className="mr-2 h-4 w-4" />
              {action.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
