import {
  Check,
  FileDiff,
  GitBranch,
  MessageSquareWarning,
  SquareTerminal,
} from "lucide-react";

const steps = [
  {
    label: "01 / PLAN",
    title: "Define scope before work starts",
    description:
      "The shared plan records the task boundary, repository constraints, owned paths, and required checks. Every run starts from the same committed plan snapshot.",
  },
  {
    label: "02 / RUN",
    title: "Assign bounded work with a trace",
    description:
      "Each agent receives one plan entry. Its run trace preserves commands, touched files, check results, and the resulting commit hash for inspection.",
  },
  {
    label: "03 / REVIEW",
    title: "Assemble changes as reviewable diffs",
    description:
      "Completed runs are grouped back under their plan entries as file-level hunks. Failed checks and unresolved comments remain explicit approval blockers.",
  },
];

function ReviewRow({
  line,
  marker,
  children,
  attention = false,
}: {
  line: string;
  marker?: "+" | "−";
  children: React.ReactNode;
  attention?: boolean;
}) {
  return (
    <div
      className={`grid grid-cols-[4rem_1fr] border-t border-border ${
        attention ? "bg-accent" : "bg-card"
      }`}
    >
      <div className="flex items-start justify-end gap-2 border-r border-border px-5 py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
        <span>{marker}</span>
        <span>{line}</span>
      </div>
      <div className="min-w-0 px-5 py-3 font-mono text-xs font-medium leading-5 text-foreground">
        {children}
      </div>
    </div>
  );
}

export default function FeatureDetail() {
  return (
    <section
      className="bg-muted py-20 md:py-28 lg:py-32"
      aria-labelledby="feature-detail-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-start gap-5 md:gap-8 lg:grid-cols-[0.82fr_1.18fr]">
          <div className="space-y-8 md:space-y-10">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                Shared execution plan
              </p>
              <h2
                id="feature-detail-heading"
                className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl"
              >
                One plan keeps parallel changes reviewable.
              </h2>
              <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                The harness ties every assignment, command, and diff hunk to a
                versioned plan entry. Reviewers can verify why a change exists,
                which run produced it, and what still requires a decision.
              </p>
            </div>

            <ol className="space-y-8 md:space-y-10">
              {steps.map((step) => (
                <li
                  key={step.label}
                  className="border-l-2 border-primary pl-5"
                >
                  <div className="space-y-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      {step.label}
                    </p>
                    <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                      {step.title}
                    </h3>
                    <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <figure className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-card px-5 py-5 sm:px-8">
              <div className="flex items-center gap-2">
                <GitBranch
                  className="h-4 w-4 text-primary"
                  aria-hidden="true"
                />
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                  review/auth-session-boundary
                </span>
              </div>
              <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                packet rp_1842
              </span>
            </div>

            <div className="grid gap-5 p-5 sm:p-8">
              <div className="rounded-md border border-border bg-muted">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3">
                  <div className="flex items-center gap-2">
                    <Check
                      className="h-4 w-4 text-primary"
                      aria-hidden="true"
                    />
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      Plan / entry resolved
                    </span>
                  </div>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    plan@8d21c6a
                  </span>
                </div>
                <div className="space-y-3 px-5 py-5">
                  <p className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                    Isolate session renewal from request handlers
                  </p>
                  <div className="grid gap-5 md:grid-cols-2 md:gap-8">
                    <div className="space-y-3">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                        Owned paths
                      </p>
                      <p className="font-mono text-xs font-medium leading-5 text-foreground">
                        src/auth/session.ts
                        <br />
                        src/auth/session.test.ts
                      </p>
                    </div>
                    <div className="space-y-3">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                        Required check
                      </p>
                      <p className="font-mono text-xs font-medium leading-5 text-foreground">
                        pnpm test session
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-md border border-border bg-card">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3">
                  <div className="flex items-center gap-2">
                    <SquareTerminal
                      className="h-4 w-4 text-primary"
                      aria-hidden="true"
                    />
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      Run / run_01J8F4K2
                    </span>
                  </div>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                    checks passed +2
                  </span>
                </div>
                <div className="grid gap-5 px-5 py-5 md:grid-cols-2 md:gap-8">
                  <div className="space-y-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                      Trace
                    </p>
                    <p className="font-mono text-xs font-medium leading-5 text-foreground">
                      $ pnpm test session
                      <br />
                      + 18 passed
                    </p>
                  </div>
                  <div className="space-y-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                      Result
                    </p>
                    <p className="font-mono text-xs font-medium leading-5 text-foreground">
                      commit 31b86e4
                      <br />
                      +2 files changed
                    </p>
                  </div>
                </div>
              </div>

              <div className="overflow-hidden rounded-md border border-border bg-card">
                <div className="flex flex-wrap items-center justify-between gap-2 bg-primary px-5 py-3">
                  <div className="flex items-center gap-2 text-primary-foreground">
                    <FileDiff className="h-4 w-4" aria-hidden="true" />
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                      Review / src/auth/session.ts
                    </span>
                  </div>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary-foreground">
                    @@ -42,6 +42,9 @@
                  </span>
                </div>

                <ReviewRow line="42">
                  export async function renewSession(
                </ReviewRow>
                <ReviewRow line="43">session: Session,</ReviewRow>
                <ReviewRow line="44" marker="+">
                  + signal: AbortSignal,
                </ReviewRow>
                <ReviewRow line="45" marker="+">
                  + clock: Clock = systemClock,
                </ReviewRow>
                <ReviewRow line="46" marker="−">
                  − if (Date.now() &gt; session.expiresAt) &#123;
                </ReviewRow>
                <ReviewRow line="47" marker="+">
                  + if (clock.now() &gt; session.expiresAt) &#123;
                </ReviewRow>
                <ReviewRow line="48" attention>
                  <span className="flex items-start gap-2">
                    <MessageSquareWarning
                      className="h-4 w-4 shrink-0 text-foreground"
                      aria-hidden="true"
                    />
                    <span>
                      Review required: confirm the injected clock remains scoped
                      to authentication code.
                    </span>
                  </span>
                </ReviewRow>
              </div>
            </div>

            <figcaption className="border-t border-border bg-muted px-5 py-5 font-body text-sm font-normal leading-6 text-muted-foreground sm:px-8">
              The review packet preserves the plan revision, run trace, commit,
              file path, diff hunk, and unresolved human checkpoint in one
              artifact.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
