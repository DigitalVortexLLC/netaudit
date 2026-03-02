import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import type { Tag } from "@/types";

interface TagSelectorProps {
  allTags: Tag[];
  selectedTagIds: number[];
  onAddTag: (data: { tag_id?: number; name?: string }) => void;
  isPending?: boolean;
}

export function TagSelector({ allTags, selectedTagIds, onAddTag, isPending }: TagSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const availableTags = allTags.filter((t) => !selectedTagIds.includes(t.id));
  const exactMatch = allTags.some((t) => t.name.toLowerCase() === search.toLowerCase());

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" disabled={isPending}>
          <Plus className="h-3 w-3 mr-1" />
          Add tag
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search or create..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>
              {search.trim() && !exactMatch ? (
                <button
                  className="w-full px-2 py-1.5 text-sm text-left hover:bg-accent"
                  onClick={() => {
                    onAddTag({ name: search.trim() });
                    setSearch("");
                    setOpen(false);
                  }}
                >
                  Create &ldquo;{search.trim()}&rdquo;
                </button>
              ) : (
                "No tags found."
              )}
            </CommandEmpty>
            <CommandGroup>
              {availableTags.map((tag) => (
                <CommandItem
                  key={tag.id}
                  value={tag.name}
                  onSelect={() => {
                    onAddTag({ tag_id: tag.id });
                    setOpen(false);
                  }}
                >
                  {tag.name}
                </CommandItem>
              ))}
              {search.trim() && !exactMatch && availableTags.length > 0 && (
                <CommandItem
                  value={`create-${search}`}
                  onSelect={() => {
                    onAddTag({ name: search.trim() });
                    setSearch("");
                    setOpen(false);
                  }}
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Create &ldquo;{search.trim()}&rdquo;
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
