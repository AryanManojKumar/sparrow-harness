import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Check,
  CircleDot,
  FileCode,
  Folder,
  GitBranch,
  GitPullRequest,
  MessageSquare,
  Network,
  Play,
} from "lucide-react";

const agents = [
  {
    agent: "agent-api",
    workspace: "workspaces/key-api",
    task: "Add dual-key verification",
    commit: "a81c9e2",
    state: "ready",
  },
  {
    agent: "agent-web",
    workspace: "workspaces/key-web",
    task: "Surface session refresh state",
    commit: "d37f4b1",
    state: "running",
  },
  {
    agent: "agent-infra",
    workspace: "workspaces/key-infra",
    task: "Stage signing-key rotation",
    commit: "c04bd78",
    state: "ready",
  },
];

const diffLines = [
  {
    line: "48",
    sign: " ",
    content: "export async function verifySession(token: string) {",
    emphasis: false,
  },
  {
    line: "49",
    sign: "-",
    content: "  return verify(token, env.SIGNING_KEY)",
    emphasis: false,
  },
  {
    line: "49",
    sign: "+",
    content: "  const keys = await signingKeys.active()",
    emphasis: true,
  },
  {
    line: "50",
    sign: "+",
    content: "  return verifyAgainstAny(token, keys)",
    emphasis: true,
  },
  {
    line: "51",
    sign: " ",
    content: "}",
    emphasis: false,
  },
];

export default function ProductShowcase() {
  return (
    <section
      aria-labelledby="product-showcase-title"
      className="bg-background py-20 text-foreground md:py-28 lg:py-32"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-end gap-5 md:grid-cols-12 md:gap-8">
          <div className="space-y-3 md:col-span-8">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              Command center / run_8H2K
            </p>
            <h2
              id="product-showcase-title"
              className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] md:text-5xl"
            >
              Coordinate the fleet. Inspect every patch.
            </h2>
            <p className="max-w-3xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              A shared plan assigns bounded work to isolated workspaces. Run traces
              show what each agent changed, while file-level diffs and approval
              checkpoints keep the merge decision with your team.
            </p>
          </div>

          <div className="md:col-span-4 md:flex md:justify-end">
            <Link
              href="/start"
              className="inline-flex items-center gap-2 rounded-md border border-foreground bg-accent px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-[box-shadow] duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Start free
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="mt-8 grid gap-5 md:mt-10 md:grid-cols-12 md:gap-8">
          <article className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] md:col-span-7">
            <header className="flex items-start justify-between gap-2 border-b border-border bg-muted px-5 py-3">
              <div className="flex items-center gap-2">
                <Network aria-hidden="true" className="h-4 w-4 text-primary" />
                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                    Parallel agents
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    Shared task: rotate signing keys without interrupting sessions
                  </p>
                </div>
              </div>
              <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                run_8H2K
              </span>
            </header>

            <div className="p-5">
              <div className="relative border-l-2 border-primary">
                <span
                  aria-hidden="true"
                  className="absolute left-0 top-5 h-3 w-3 -translate-x-2 border border-foreground bg-accent"
                />
                <div className="divide-y divide-border">
                  {agents.map((agent) => (
                    <div
                      key={agent.agent}
                      className="grid gap-5 px-5 py-3 md:grid-cols-[1fr_1fr_auto]"
                    >
                      <div className="flex items-start gap-2">
                        <span
                          aria-hidden="true"
                          className={`mt-3 h-2 w-2 rounded-full border border-foreground ${
                            agent.state === "ready" ? "bg-primary" : "bg-accent"
                          }`}
                        />
                        <div>
                          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                            {agent.agent}
                          </p>
                          <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                            {agent.task}
                          </p>
                        </div>
                      </div>
                      <div>
                        <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                          {agent.workspace}
                        </p>
                        <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                          commit {agent.commit}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                        {agent.state === "ready" ? (
                          <Check aria-hidden="true" className="h-4 w-4 text-primary" />
                        ) : (
                          <Play aria-hidden="true" className="h-4 w-4 text-foreground" />
                        )}
                        {agent.state}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>

          <article className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] md:col-span-5">
            <header className="flex items-start justify-between gap-2 border-b border-border bg-muted px-5 py-3">
              <div className="flex items-center gap-2">
                <Folder aria-hidden="true" className="h-4 w-4 text-primary" />
                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                    Workspace map
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    acme/platform · branch key-rotation
                  </p>
                </div>
              </div>
              <GitBranch aria-hidden="true" className="h-4 w-4 text-muted-foreground" />
            </header>

            <div className="p-5">
              <div className="relative space-y-3 border-l-2 border-primary px-5">
                <span
                  aria-hidden="true"
                  className="absolute left-0 top-3 h-3 w-3 -translate-x-2 border border-foreground bg-accent"
                />
                <div className="border border-border bg-muted px-5 py-3">
                  <div className="flex items-center gap-2">
                    <Folder aria-hidden="true" className="h-4 w-4 text-primary" />
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                      workspaces/key-api
                    </p>
                  </div>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    packages/auth · 3 files changed
                  </p>
                </div>
                <div className="border border-border px-5 py-3">
                  <div className="flex items-center gap-2">
                    <Folder aria-hidden="true" className="h-4 w-4 text-primary" />
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                      workspaces/key-web
                    </p>
                  </div>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    apps/console · run in progress
                  </p>
                </div>
                <div className="border border-border px-5 py-3">
                  <div className="flex items-center gap-2">
                    <Folder aria-hidden="true" className="h-4 w-4 text-primary" />
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                      workspaces/key-infra
                    </p>
                  </div>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    infra/keys · 2 files changed
                  </p>
                </div>
              </div>
            </div>
          </article>

          <article className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] md:col-span-5">
            <header className="flex items-start justify-between gap-2 border-b border-border bg-muted px-5 py-3">
              <div className="flex items-center gap-2">
                <Bot aria-hidden="true" className="h-4 w-4 text-primary" />
                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                    Coordination trace
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    Plan constraints shared across all runs
                  </p>
                </div>
              </div>
              <CircleDot aria-hidden="true" className="h-4 w-4 text-accent" />
            </header>

            <div className="p-5">
              <div className="relative border-l-2 border-primary px-5">
                <span
                  aria-hidden="true"
                  className="absolute left-0 top-5 h-3 w-3 -translate-x-2 border border-foreground bg-accent"
                />
                <div className="space-y-3">
                  <div className="border border-border px-5 py-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      plan / constraint accepted
                    </p>
                    <p className="font-body text-sm font-normal leading-6">
                      Preserve verification for the current and previous signing key.
                    </p>
                  </div>
                  <div className="border border-border px-5 py-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      run / dependency resolved
                    </p>
                    <p className="font-body text-sm font-normal leading-6">
                      agent-web reads the API contract from commit{" "}
                      <span className="font-mono">a81c9e2</span>.
                    </p>
                  </div>
                  <div className="border border-accent bg-muted px-5 py-3">
                    <p className="flex items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                      <MessageSquare aria-hidden="true" className="h-4 w-4 text-accent" />
                      review / decision required
                    </p>
                    <p className="font-body text-sm font-normal leading-6">
                      Confirm the overlap window before the infrastructure patch can
                      enter the merge set.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] md:col-span-7">
            <header className="flex items-start justify-between gap-2 border-b border-border bg-muted px-5 py-3">
              <div className="flex items-center gap-2">
                <GitPullRequest aria-hidden="true" className="h-4 w-4 text-primary" />
                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                    Explicit diff review
                  </p>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    packages/auth/src/keys.ts
                  </p>
                </div>
              </div>
              <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                a81c9e2
              </span>
            </header>

            <div className="p-5">
              <div className="relative overflow-hidden border-l-2 border-primary">
                <span
                  aria-hidden="true"
                  className="absolute left-0 top-8 h-3 w-3 -translate-x-2 border border-foreground bg-accent"
                />
                <div className="flex items-center gap-2 border-b border-border bg-muted px-5 py-3">
                  <FileCode aria-hidden="true" className="h-4 w-4 text-primary" />
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                    @@ -48,5 +48,6 @@ verifySession
                  </p>
                </div>

                <div>
                  {diffLines.map((line, index) => (
                    <div
                      key={`${line.line}-${index}`}
                      className={`grid grid-cols-[auto_auto_1fr] border-b border-border px-5 py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] last:border-b-0 ${
                        line.emphasis ? "bg-muted text-primary" : ""
                      }`}
                    >
                      <span className="w-8 text-muted-foreground">{line.line}</span>
                      <span className="w-5" aria-label={line.sign === "+" ? "Added" : line.sign === "-" ? "Removed" : undefined}>
                        {line.sign}
                      </span>
                      <code className="overflow-x-auto whitespace-pre">
                        {line.content}
                      </code>
                    </div>
                  ))}
                </div>

                <div className="flex items-start gap-2 border-t border-accent bg-muted px-5 py-3">
                  <MessageSquare
                    aria-hidden="true"
                    className="h-4 w-4 text-accent"
                  />
                  <div>
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                      unresolved · security-review
                    </p>
                    <p className="font-body text-sm font-normal leading-6">
                      Require a bounded expiry on the previous key before approval.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
