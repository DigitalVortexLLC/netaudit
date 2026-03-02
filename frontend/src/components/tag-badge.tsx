import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const TAG_COLORS = [
  "bg-blue-500/20 text-blue-300",
  "bg-green-500/20 text-green-300",
  "bg-yellow-500/20 text-yellow-300",
  "bg-red-500/20 text-red-300",
  "bg-purple-500/20 text-purple-300",
  "bg-pink-500/20 text-pink-300",
  "bg-indigo-500/20 text-indigo-300",
  "bg-orange-500/20 text-orange-300",
  "bg-teal-500/20 text-teal-300",
  "bg-cyan-500/20 text-cyan-300",
];

function hashTagName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function getTagColorClass(name: string): string {
  return TAG_COLORS[hashTagName(name) % TAG_COLORS.length];
}

interface TagBadgeProps {
  name: string;
  onRemove?: () => void;
  className?: string;
}

export function TagBadge({ name, onRemove, className }: TagBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        getTagColorClass(name),
        className
      )}
    >
      {name}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="hover:opacity-70 -mr-1"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
