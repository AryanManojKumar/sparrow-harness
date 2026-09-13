import { LayoutGrid } from "lucide-react";

import { SparrowMark } from "@/components/sparrow-mark";

export function TopBar() {
  return (
    <header className="flex items-center justify-between px-6 py-4">
      <div className="flex items-center gap-2 text-sm text-foreground">
        <SparrowMark className="size-5" />
        <span className="font-medium">sparrow</span>
        <span className="mx-2 h-4 w-px bg-border" />
        <LayoutGrid className="size-4 text-muted-foreground" />
        <span className="text-muted-foreground">Home</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex size-8 items-center justify-center rounded-full bg-secondary text-xs font-medium text-secondary-foreground">
          A
        </div>
      </div>
    </header>
  );
}
