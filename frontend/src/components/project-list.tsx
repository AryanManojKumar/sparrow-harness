import { RECENT_PROJECTS } from "@/lib/projects";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, string> = {
  building: "bg-amber-400/15 text-amber-300",
  ready: "bg-emerald-400/15 text-emerald-300",
  "needs input": "bg-sky-400/15 text-sky-300",
};

export function ProjectList() {
  if (RECENT_PROJECTS.length === 0) return null;

  return (
    <div className="mx-auto mt-16 w-full max-w-2xl">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">Recent</h2>
      <ul className="flex flex-col gap-2">
        {RECENT_PROJECTS.map((p) => (
          <li key={p.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-xl border border-border bg-card/50 px-4 py-3 text-left transition-colors hover:bg-card"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{p.name}</p>
                <p className="text-xs text-muted-foreground">{p.updatedLabel}</p>
              </div>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                  STATUS_STYLE[p.status]
                )}
              >
                {p.status}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
