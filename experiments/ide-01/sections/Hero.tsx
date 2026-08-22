import { ArrowRight, BookOpen, Check, MessageSquare } from "lucide-react";

export default function Hero() {
  return (
    <section className="overflow-hidden bg-background py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-center gap-5 md:gap-8 lg:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
          <div className="space-y-8 md:space-y-10">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                Developer preview / agent harness
              </p>

              <h1 className="font-display text-5xl font-semibold leading-[0.94] tracking-[-0.045em] text-foreground md:text-7xl">
                Coding agents, under one reviewable plan.
              </h1>

              <p className="max-w-3xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Run a fleet against your repository without merging their work
                into a black box. Each task is assigned from a shared plan,
                traced to a run, and held as a file-level diff before it can
                land.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <a
                href="/signup"
                className="inline-flex items-center gap-2 rounded-md border border-foreground bg-accent px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-[box-shadow] duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                Start free
                <ArrowRight aria-hidden="true" className="size-4" />
              </a>

              <a
                href="/docs"
                className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-[box-shadow] duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
              >
                <BookOpen aria-hidden="true" className="size-4 text-primary" />
                Read the docs
              </a>
            </div>
          </div>

          <div className="lg:w-[calc(100%+2rem)] xl:w-[calc(100%+((100vw-80rem)/2)+2rem)]">
            <div
              className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]"
              aria-label="Review packet showing a shared plan, assigned agent runs, a file-level diff, and an unresolved human review checkpoint"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3 sm:px-8">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="size-2 rounded-full bg-primary"
                  />
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                    RUN / run_01842
                  </span>
                </div>
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  branch: plan/authz-cache
                </span>
              </div>

              <div className="grid md:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)]">
                <div className="space-y-8 border-b border-border p-5 sm:p-8 md:border-b-0 md:border-r">
                  <div className="space-y-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      PLAN / shared-plan.yaml
                    </p>
                    <h2 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                      Cache authorization checks
                    </h2>
                    <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                      Preserve tenant boundaries while moving repeated policy
                      reads behind the repository cache interface.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-start gap-2">
                      <Check
                        aria-hidden="true"
                        className="mt-1 size-4 text-primary"
                      />
                      <div>
                        <p className="font-mono text-sm font-medium leading-6 text-foreground">
                          task/authz-interface
                        </p>
                        <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                          assigned → agent-02
                        </p>
                      </div>
                    </div>

                    <div className="flex items-start gap-2">
                      <Check
                        aria-hidden="true"
                        className="mt-1 size-4 text-primary"
                      />
                      <div>
                        <p className="font-mono text-sm font-medium leading-6 text-foreground">
                          task/cache-tests
                        </p>
                        <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                          assigned → agent-05
                        </p>
                      </div>
                    </div>

                    <div className="border-l-2 border-accent bg-muted px-5 py-3">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                        REVIEW REQUIRED
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        Confirm invalidation scope before approval.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3 sm:px-8">
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      REVIEW / src/authz/cache.ts
                    </span>
                    <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                      8f31c2a
                    </span>
                  </div>

                  <div className="relative border-l-2 border-primary bg-muted py-3">
                    <span
                      aria-hidden="true"
                      className="absolute left-0 top-[62%] size-3 -translate-x-1/2 border border-foreground bg-accent"
                    />

                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] px-5 font-mono text-sm leading-6 text-muted-foreground sm:px-8">
                      <span>41</span>
                      <span className="text-primary">
                        @@ -41,6 +41,12 @@
                      </span>
                    </div>
                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] px-5 font-mono text-sm leading-6 text-foreground sm:px-8">
                      <span className="text-muted-foreground">42</span>
                      <span>export async function canAccess(</span>
                    </div>
                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] px-5 font-mono text-sm leading-6 text-foreground sm:px-8">
                      <span className="text-muted-foreground">43</span>
                      <span>&nbsp;&nbsp;tenantId: TenantId,</span>
                    </div>
                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] bg-card px-5 font-mono text-sm leading-6 sm:px-8">
                      <span className="text-muted-foreground">44</span>
                      <span className="text-primary">
                        + const key = policyKey(tenantId, subject)
                      </span>
                    </div>
                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] bg-card px-5 font-mono text-sm leading-6 sm:px-8">
                      <span className="text-muted-foreground">45</span>
                      <span className="text-primary">
                        + const cached = await policyCache.get(key)
                      </span>
                    </div>
                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] bg-card px-5 font-mono text-sm leading-6 sm:px-8">
                      <span className="text-muted-foreground">46</span>
                      <span className="text-primary">
                        + if (cached) return cached.decision
                      </span>
                    </div>
                    <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] px-5 font-mono text-sm leading-6 text-foreground sm:px-8">
                      <span className="text-muted-foreground">47</span>
                      <span>&nbsp;&nbsp;return evaluatePolicy(subject)</span>
                    </div>
                  </div>

                  <div className="flex items-start gap-2 border-t border-border bg-card p-5 sm:p-8">
                    <MessageSquare
                      aria-hidden="true"
                      className="mt-1 size-4 text-accent"
                    />
                    <div className="space-y-3">
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                        CHECKPOINT / staff-review
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        Tenant-scoped key is correct. Add invalidation on role
                        mutation, then request approval again.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border bg-muted px-5 py-3 sm:px-8">
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  2 runs · 1 diff · 1 unresolved comment
                </span>
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                  merge blocked
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
