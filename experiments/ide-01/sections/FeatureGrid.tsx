import type { LucideIcon } from "lucide-react";
import {
  FileDiff,
  GitBranch,
  History,
  ListTree,
  MessageSquareWarning,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  artifact: string;
  title: string;
  body: string;
  checkpoint?: string;
};

const features: Feature[] = [
  {
    icon: ListTree,
    artifact: "plan/shared-plan.yml",
    title: "One plan, explicit ownership",
    body: "The shared plan records scope, acceptance checks, and an assigned run for each task before an agent touches the repository.",
  },
  {
    icon: GitBranch,
    artifact: "run/run_18f4",
    title: "Isolated repository runs",
    body: "Each agent works from a pinned base commit in its own worktree, so concurrent edits remain attributable and can be discarded independently.",
  },
  {
    icon: TerminalSquare,
    artifact: "trace/run_18f4.jsonl",
    title: "Commands stay inspectable",
    body: "Run traces retain executed commands, test results, changed paths, and task context under a stable run ID for later review.",
  },
  {
    icon: FileDiff,
    artifact: "diff/src/auth/session.ts",
    title: "Review the patch, not a summary",
    body: "Proposed work is assembled into file-level hunks with line numbers and run provenance, preserving the evidence needed for code review.",
  },
  {
    icon: MessageSquareWarning,
    artifact: "review/checkpoint_07",
    title: "Unresolved decisions block landing",
    body: "Comments and failed acceptance checks attach to the affected hunk. The candidate branch cannot advance until a reviewer resolves them.",
    checkpoint: "review required",
  },
  {
    icon: History,
    artifact: "base/8c14a2f",
    title: "Conflicts return to the plan",
    body: "Overlapping edits are compared against the pinned base commit and routed back as explicit plan items instead of being silently merged.",
    checkpoint: "decision required",
  },
];

export default function FeatureGrid() {
  return (
    <section
      className="bg-background py-20 md:py-28 lg:py-32"
      aria-labelledby="feature-grid-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="space-y-8 md:space-y-10">
          <div className="max-w-3xl space-y-3">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              Reviewable by construction
            </p>
            <h2
              id="feature-grid-heading"
              className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl"
            >
              Every capability leaves an artifact.
            </h2>
            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Plans, runs, and proposed changes remain connected through repository
              paths, run IDs, and review checkpoints. Engineers can inspect the
              mechanism behind each result before it lands.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 md:gap-8 lg:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <article
                  key={feature.title}
                  className="h-full rounded-md border border-l-4 border-border border-l-primary bg-card p-5 shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-[box-shadow] duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] md:p-8"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <Icon
                          aria-hidden="true"
                          className="h-5 w-5 shrink-0 text-primary"
                          strokeWidth={2}
                        />
                        <span className="truncate font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                          {feature.artifact}
                        </span>
                      </div>

                      {feature.checkpoint ? (
                        <span
                          className="flex shrink-0 items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-accent"
                          aria-label={feature.checkpoint}
                        >
                          <ShieldCheck
                            aria-hidden="true"
                            className="h-5 w-5"
                            strokeWidth={2}
                          />
                          <span className="hidden md:inline">
                            {feature.checkpoint}
                          </span>
                        </span>
                      ) : null}
                    </div>

                    <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                      {feature.title}
                    </h3>

                    <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                      {feature.body}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
