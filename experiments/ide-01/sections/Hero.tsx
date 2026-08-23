import {
  ArrowRight,
  BookOpen,
  Check,
  GitBranch,
  MessageSquare,
} from "lucide-react";

export default function Hero() {
  return (
    <section
      aria-labelledby="hero-heading"
      className="bg-background py-20 md:py-28 lg:py-32"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-center gap-5 md:gap-8 lg:grid-cols-[0.82fr_1.18fr]">
          <div className="space-y-8 md:space-y-10">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                Agent harness / Developer preview
              </p>

              <h1
                id="hero-heading"
                className="font-display text-5xl font-semibold leading-[0.94] tracking-[-0.045em] text-foreground md:text-7xl"
              >
                Run coding agents under one reviewable plan.
              </h1>

              <p className="max-w-3xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Coordinate a fleet against your repository while every task
                stays tied to an owner, run ID, and file-level diff. Nothing
                lands until an engineer approves the patch.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <a
                href="/start"
                className="inline-flex items-center gap-2 rounded-md border border-accent bg-accent px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-[box-shadow] duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Start free
                <ArrowRight aria-hidden="true" className="size-4" />
              </a>

              <a
                href="/docs"
                className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-[box-shadow] duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                <BookOpen aria-hidden="true" className="size-4 text-primary" />
                Read the docs
              </a>
            </div>
          </div>

          <figure className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]">
            <figcaption className="space-y-3 border-b border-border p-5 md:p-8">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <GitBranch
                    aria-hidden="true"
                    className="size-4 text-primary"
                  />
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                    acme/payments
                  </span>
                </div>

                <span className="inline-flex items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  <span
                    aria-hidden="true"
                    className="size-2 rounded-full bg-primary"
                  />
                  run/8f3c1 active
                </span>
              </div>

              <div className="grid gap-5 border-t border-border pt-3 md:grid-cols-2 md:gap-8">
                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    Shared plan
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-foreground">
                    Guard duplicate capture requests
                  </p>
                </div>

                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    Assigned run
                  </p>
                  <p className="font-mono text-xs font-normal leading-5 text-foreground">
                    agent/payments-02
                  </p>
                </div>
              </div>
            </figcaption>

            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3">
              <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                services/payments/capture.ts
              </span>
              <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                +4 proposed
              </span>
            </div>

            <div className="overflow-x-auto">
              <div className="min-w-[32rem] font-mono text-xs font-normal leading-5">
                <div className="grid grid-cols-[auto_1fr_auto] border-b border-border bg-muted text-muted-foreground">
                  <span className="border-r border-border px-5 py-3">41</span>
                  <code className="border-l-2 border-primary px-5 py-3">
                    @@ -41,6 +41,10 @@ async function capture(request)
                  </code>
                  <span className="px-5 py-3 text-primary">hunk</span>
                </div>

                <div className="grid grid-cols-[auto_1fr_auto] border-b border-border text-foreground">
                  <span className="border-r border-border px-5 py-3 text-muted-foreground">
                    44
                  </span>
                  <code className="border-l-2 border-primary px-5 py-3">
                    <span className="text-primary">+</span> const prior =
                    await captures.byKey(request.idempotencyKey)
                  </code>
                  <span className="px-5 py-3 text-primary">+</span>
                </div>

                <div className="grid grid-cols-[auto_1fr_auto] border-b border-border bg-muted text-foreground">
                  <span className="border-r border-border px-5 py-3 text-muted-foreground">
                    45
                  </span>
                  <code className="border-l-2 border-primary px-5 py-3">
                    <span className="text-primary">+</span> if (prior) return
                    prior
                  </code>
                  <span className="px-5 py-3 text-primary">+</span>
                </div>

                <div className="grid grid-cols-[auto_1fr_auto] border-b border-border text-foreground">
                  <span className="border-r border-border px-5 py-3 text-muted-foreground">
                    46
                  </span>
                  <code className="border-l-2 border-primary px-5 py-3">
                    <span className="text-primary">+</span> await
                    captures.reserve(request.idempotencyKey)
                  </code>
                  <span className="px-5 py-3 text-primary">+</span>
                </div>

                <div className="grid grid-cols-[auto_1fr_auto] bg-muted text-foreground">
                  <span className="border-r border-border px-5 py-3 text-muted-foreground">
                    47
                  </span>
                  <code className="border-l-2 border-primary px-5 py-3">
                    return gateway.capture(request)
                  </code>
                  <span className="px-5 py-3 text-muted-foreground">·</span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border p-5 md:p-8">
              <div className="flex items-center gap-2 text-foreground">
                <span className="inline-flex rounded-sm border border-accent bg-accent p-3">
                  <MessageSquare aria-hidden="true" className="size-4" />
                </span>
                <div>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
                    Review required
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    Confirm reservation cleanup on gateway failure.
                  </p>
                </div>
              </div>

              <span className="inline-flex items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                <Check aria-hidden="true" className="size-4" />
                checks passed
              </span>
            </div>
          </figure>
        </div>
      </div>
    </section>
  );
}
