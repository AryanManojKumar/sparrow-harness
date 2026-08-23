import type { ReactNode } from "react";

type CapabilityCardProps = {
  title: string;
  description: string;
  artifactLabel: string;
  artifactMeta: string;
  className?: string;
  children: ReactNode;
};

function CapabilityCard({
  title,
  description,
  artifactLabel,
  artifactMeta,
  className = "",
  children,
}: CapabilityCardProps) {
  return (
    <article
      className={`rounded-md border border-border bg-card p-5 shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] md:p-8 ${className}`}
    >
      <div className="space-y-8">
        <div className="space-y-3">
          <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
            {title}
          </h3>
          <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
            {description}
          </p>
        </div>

        <div className="overflow-hidden rounded-md border border-border bg-background">
          <div className="flex items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3">
            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
              {artifactLabel}
            </span>
            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
              {artifactMeta}
            </span>
          </div>
          {children}
        </div>
      </div>
    </article>
  );
}

function ArtifactLine({
  number,
  marker,
  markerClassName,
  children,
  status,
}: {
  number: string;
  marker: string;
  markerClassName: string;
  children: ReactNode;
  status?: ReactNode;
}) {
  return (
    <div className="flex items-start gap-2 border-l-2 border-primary px-5 py-3">
      <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
        {number}
      </span>
      <span
        className={`font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] ${markerClassName}`}
        aria-hidden="true"
      >
        {marker}
      </span>
      <span className="min-w-0 flex-1 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
        {children}
      </span>
      {status}
    </div>
  );
}

export default function FeatureGrid() {
  return (
    <section className="bg-muted py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="space-y-8 md:space-y-10">
          <header className="max-w-7xl space-y-3">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              Harness capabilities / evidence attached
            </p>
            <h2 className="max-w-7xl font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl">
              Plugins extend execution. Run records preserve the evidence.
            </h2>
            <p className="max-w-7xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Each agent works from the same repository plan, through explicit
              extension points, with its commands, outputs, commits, and review
              state retained as inspectable artifacts.
            </p>
          </header>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 md:gap-8 lg:grid-cols-6">
            <CapabilityCard
              title="One plan, checked into the repository"
              description="Plan entries name the intended files, acceptance checks, and human checkpoints. Agents claim entries rather than inventing a separate task list."
              artifactLabel=".harness/plan.yaml"
              artifactMeta="plan@84c1"
              className="lg:col-span-2"
            >
              <div className="divide-y divide-border">
                <ArtifactLine
                  number="08"
                  marker="+"
                  markerClassName="text-primary"
                  status={
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      ✓ scoped
                    </span>
                  }
                >
                  task: isolate token refresh
                </ArtifactLine>
                <ArtifactLine
                  number="09"
                  marker="+"
                  markerClassName="text-primary"
                >
                  paths: src/auth/**, tests/auth/**
                </ArtifactLine>
                <ArtifactLine
                  number="10"
                  marker="!"
                  markerClassName="text-foreground"
                  status={
                    <span className="border border-accent bg-accent px-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      review
                    </span>
                  }
                >
                  checkpoint: migration boundary
                </ArtifactLine>
              </div>
            </CapabilityCard>

            <CapabilityCard
              title="Parallel runs keep ownership explicit"
              description="Each claimed plan entry receives an agent, branch, and run ID. File scopes show collisions before independently proposed changes are combined."
              artifactLabel="run fleet"
              artifactMeta="3 active"
              className="lg:col-span-2"
            >
              <div className="divide-y divide-border">
                <ArtifactLine
                  number="01"
                  marker="+"
                  markerClassName="text-primary"
                  status={
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      ● running
                    </span>
                  }
                >
                  agent-02 / run_7F31
                </ArtifactLine>
                <ArtifactLine
                  number="02"
                  marker="+"
                  markerClassName="text-primary"
                >
                  branch: harness/token-refresh
                </ArtifactLine>
                <ArtifactLine
                  number="03"
                  marker="!"
                  markerClassName="text-foreground"
                  status={
                    <span className="border border-accent bg-accent px-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      conflict
                    </span>
                  }
                >
                  src/auth/session.ts
                </ArtifactLine>
              </div>
            </CapabilityCard>

            <CapabilityCard
              title="Plugins declare where they intervene"
              description="Checked-in plugin configuration registers tools, policy checks, and lifecycle hooks. A run record identifies the exact plugin version invoked."
              artifactLabel="harness.config.ts"
              artifactMeta="plugin graph"
              className="lg:col-span-2"
            >
              <div className="divide-y divide-border">
                <ArtifactLine
                  number="14"
                  marker="+"
                  markerClassName="text-primary"
                >
                  plugin: &quot;schema-guard@2.4.1&quot;
                </ArtifactLine>
                <ArtifactLine
                  number="15"
                  marker="+"
                  markerClassName="text-primary"
                >
                  hook: &quot;before_apply&quot;
                </ArtifactLine>
                <ArtifactLine
                  number="16"
                  marker="+"
                  markerClassName="text-primary"
                  status={
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      ✓ loaded
                    </span>
                  }
                >
                  command: &quot;pnpm db:check&quot;
                </ArtifactLine>
              </div>
            </CapabilityCard>

            <CapabilityCard
              title="Every run leaves an inspectable record"
              description="The record connects the plan entry to prompts, tool calls, command output, changed paths, and the resulting commit. Reviewers can trace a change without replaying the agent."
              artifactLabel="runs/run_7F31/record"
              artifactMeta="commit 91ae20b"
              className="lg:col-span-3"
            >
              <div className="divide-y divide-border">
                <ArtifactLine
                  number="21"
                  marker="+"
                  markerClassName="text-primary"
                  status={
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      ✓ exit 0
                    </span>
                  }
                >
                  $ pnpm test auth --runInBand
                </ArtifactLine>
                <ArtifactLine
                  number="22"
                  marker="+"
                  markerClassName="text-primary"
                >
                  output: 18 passed / 0 failed
                </ArtifactLine>
                <ArtifactLine
                  number="23"
                  marker="+"
                  markerClassName="text-primary"
                >
                  write: src/auth/token-store.ts
                </ArtifactLine>
                <ArtifactLine
                  number="24"
                  marker="!"
                  markerClassName="text-foreground"
                  status={
                    <span className="border border-accent bg-accent px-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      inspect
                    </span>
                  }
                >
                  tool call: schema-guard@2.4.1
                </ArtifactLine>
              </div>
            </CapabilityCard>

            <CapabilityCard
              title="The landing unit is a reviewable diff"
              description="Proposed changes stay grouped by plan entry and file, with test evidence beside the hunk. Unresolved comments remain visible and block approval."
              artifactLabel="src/auth/token-store.ts"
              artifactMeta="+12 −4"
              className="lg:col-span-3"
            >
              <div className="divide-y divide-border">
                <ArtifactLine
                  number="42"
                  marker="−"
                  markerClassName="text-muted-foreground"
                >
                  return cache.get(userId)
                </ArtifactLine>
                <ArtifactLine
                  number="42"
                  marker="+"
                  markerClassName="text-primary"
                >
                  return cache.get(scopedKey(userId))
                </ArtifactLine>
                <ArtifactLine
                  number="43"
                  marker="+"
                  markerClassName="text-primary"
                >
                  ?? refreshFromProvider(userId)
                </ArtifactLine>
                <ArtifactLine
                  number="44"
                  marker="!"
                  markerClassName="text-foreground"
                  status={
                    <span className="border border-accent bg-accent px-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      1 comment
                    </span>
                  }
                >
                  verify tenant scope before approval
                </ArtifactLine>
              </div>
            </CapabilityCard>
          </div>

          <div>
            <a
              href="/docs"
              className="inline-flex items-center gap-2 border-b border-primary font-body text-sm font-normal leading-6 text-primary"
            >
              Read the docs
              <span aria-hidden="true">→</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
