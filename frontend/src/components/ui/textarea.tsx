import * as React from "react";

import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "w-full resize-none bg-transparent text-base text-foreground placeholder:text-muted-foreground outline-none",
        className
      )}
      {...props}
    />
  );
}

export { Textarea };
