const mechanismPoints = [
  {
    label: "Plugin boundary",
    title: "Inputs and outputs stay attributable",
    body: "A plugin declares the repository scope, tools, model adapter, and validation hooks available to its run. The harness records that resolved configuration beside the run, so reviewers can inspect what the agent was permitted to read, execute, and change.",
  },
  {
    label: "Shared event schema",
    title: "Different agents produce one review trail",
    body: "Planning decisions, tool calls, command results, file writes, and validation outcomes enter the same event stream. The adapter may change, but the evidence presented to the team does not.",
  },
  {
    label: "Diff provenance",
    title: "Each hunk links back to its cause",
    body: "Changed lines retain the originating task, run identifier, and validation result. An unresolved assumption becomes an amber checkpoint on the affected hunk rather than disappearing into a transcript.",
  },
];

const diffLines = [
  {
    oldLine: "41",
    newLine: "41",
    marker: "−",
    code: "return client.request(route, payload)",
    tone: "muted",
  },
  {
    oldLine: "42",
    newLine: "41",
    marker: "+",
    code: "const request = withRetryPolicy(route, payload)",
    tone: "primary",
  },
  {
    oldLine: "",
    newLine: "42",
    marker: "+",
    code: "return client.request(request)",
    tone: "primary",
  },
];

export default function FeatureDetail() {
  return (
    <section
      className="bg-muted py-20 md:py-28 lg:py-32"
      aria-labelledby="feature-detail-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid gap-5 md:gap-8 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="space-y-8 md:space-y-10">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                Plugin architecture
              </p>
              <h2
                id="feature-detail-heading"
                className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl"
              >
                Everything is a plugin. Every run is traceable.
              </h2>
              <div className="space-y-3">
                <p className="font-body text-base font-normal leading-7 text-foreground md:text-lg md:leading-8">
                  Agents, repository tools, validation commands, and review
                  policies connect through explicit plugin contracts. The
                  contract is the control surface: it defines what a run can
                  access, which events it must emit, and what evidence is
                  required before its changes can be proposed.
                </p>
                <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                  That separation lets a team change an agent or add an
                  internal tool without changing how work is reviewed. Every
                  implementation still resolves into the same inspectable
                  artifacts: a run manifest, an ordered trace, file-level
                  diffs, command results, and explicit review checkpoints.
                  Reviewers evaluate the patch with its provenance attached,
                  not by reconstructing intent from a conversation log.
                </p>
              </div>
            </div>

            <div className="space-y-8 md:space-y-10">
              {mechanismPoints.map((point) => (
                <article
                  key={point.label}
                  className="border-l-2 border-primary px-5"
                >
                  <div className="space-y-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      {point.label}
                    </p>
                    <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                      {point.title}
                    </h3>
                    <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                      {point.body}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="space-y-8 md:space-y-10">
            <article
              className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]"
              aria-label="Plugin-based run mechanism"
            >
              <header className="flex items-start justify-between gap-2 border-b border-border p-5">
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                    Run manifest
                  </p>
                  <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                    Plugin contracts resolve before execution
                  </h3>
                </div>
                <span className="rounded-sm border border-primary bg-muted px-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                  ● active
                </span>
              </header>

              <div className="grid gap-5 p-5 md:grid-cols-[1fr_1fr] md:gap-8">
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    .harness/plugins/repository.ts
                  </p>
                  <div className="overflow-hidden rounded-sm border border-border bg-muted">
                    <div className="grid grid-cols-[3rem_1fr] border-b border-border p-5">
                      <span className="font-mono text-sm font-normal leading-6 text-muted-foreground">
                        07
                      </span>
                      <span className="font-mono text-sm font-normal leading-6 text-foreground">
                        plugin: repository-tools
                      </span>
                    </div>
                    <div className="grid grid-cols-[3rem_1fr] border-b border-border p-5">
                      <span className="font-mono text-sm font-normal leading-6 text-muted-foreground">
                        08
                      </span>
                      <span className="font-mono text-sm font-normal leading-6 text-foreground">
                        scope: packages/api/**
                      </span>
                    </div>
                    <div className="grid grid-cols-[3rem_1fr] border-b border-border p-5">
                      <span className="font-mono text-sm font-normal leading-6 text-muted-foreground">
                        09
                      </span>
                      <span className="font-mono text-sm font-normal leading-6 text-primary">
                        tools: [read, patch, test]
                      </span>
                    </div>
                    <div className="grid grid-cols-[3rem_1fr] p-5">
                      <span className="font-mono text-sm font-normal leading-6 text-muted-foreground">
                        10
                      </span>
                      <span className="font-mono text-sm font-normal leading-6 text-foreground">
                        review: approval-required
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    run_01JQ8F2C · trace
                  </p>
                  <div className="space-y-3 border-l-2 border-primary px-5">
                    <div>
                      <p className="font-mono text-sm font-medium leading-6 text-primary">
                        + plugin.resolved
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        Repository scope and allowed tools recorded.
                      </p>
                    </div>
                    <div>
                      <p className="font-mono text-sm font-medium leading-6 text-primary">
                        + command.completed
                      </p>
                      <p className="font-mono text-sm font-normal leading-6 text-foreground">
                        pnpm test packages/api
                      </p>
                    </div>
                    <div>
                      <p className="font-mono text-sm font-medium leading-6 text-primary">
                        + patch.proposed
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        Two hunks attached to task API-184.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <article
              className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]"
              aria-label="Traceable diff review outcome"
            >
              <header className="flex items-start justify-between gap-2 border-b border-border p-5">
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                    Diff review
                  </p>
                  <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                    The patch carries its run history
                  </h3>
                </div>
                <span className="rounded-sm border border-accent bg-accent px-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                  ! decision
                </span>
              </header>

              <div className="border-b border-border bg-muted p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-mono text-sm font-medium leading-6 text-foreground">
                    packages/api/src/client.ts
                  </p>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    run_01JQ8F2C · a84c2de
                  </p>
                </div>
              </div>

              <div className="border-l-2 border-primary">
                <div className="border-b border-border bg-muted p-5">
                  <p className="font-mono text-sm font-normal leading-6 text-primary">
                    @@ -41,2 +41,3 @@ export async function send
                  </p>
                </div>

                {diffLines.map((line) => (
                  <div
                    key={`${line.marker}-${line.newLine}-${line.code}`}
                    className={`grid grid-cols-[3rem_3rem_1fr] border-b border-border p-5 ${
                      line.tone === "primary" ? "bg-card" : "bg-muted"
                    }`}
                  >
                    <span className="font-mono text-sm font-normal leading-6 text-muted-foreground">
                      {line.oldLine}
                    </span>
                    <span className="font-mono text-sm font-normal leading-6 text-muted-foreground">
                      {line.newLine}
                    </span>
                    <code
                      className={`font-mono text-sm font-normal leading-6 ${
                        line.tone === "primary"
                          ? "text-primary"
                          : "text-foreground"
                      }`}
                    >
                      {line.marker} {line.code}
                    </code>
                  </div>
                ))}
              </div>

              <aside className="p-5">
                <div className="rounded-sm border border-accent bg-muted p-5">
                  <div className="flex items-start gap-2">
                    <span
                      className="font-mono text-sm font-medium leading-6 text-foreground"
                      aria-hidden="true"
                    >
                      !
                    </span>
                    <div className="space-y-3">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                        Review checkpoint · retry policy
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        The run introduced the repository default retry policy,
                        but the task does not specify whether POST requests are
                        safe to retry. Confirm the route constraint before
                        approval.
                      </p>
                      <p className="font-mono text-sm font-normal leading-6 text-foreground">
                        source: task API-184 · event patch.proposed
                      </p>
                    </div>
                  </div>
                </div>
              </aside>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}
