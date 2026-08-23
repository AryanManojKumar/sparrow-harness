import { CheckSquare } from "lucide-react";

export default function Testimonial() {
  return (
    <section
      aria-label="Customer evidence"
      className="bg-background py-20 md:py-28 lg:py-32"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <figure className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)]">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3 md:px-8">
            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
              evidence/adoption-review.md
            </span>
            <span className="flex items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
              <CheckSquare
                aria-hidden="true"
                className="h-5 w-5 text-accent"
                strokeWidth={2}
              />
              Customer checkpoint
            </span>
          </div>

          <div className="grid grid-cols-[auto_1fr] gap-5 px-5 py-8 md:gap-8 md:px-8 md:py-10">
            <div
              aria-hidden="true"
              className="space-y-3 border-r border-primary pr-5 text-right font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground"
            >
              <div>41</div>
              <div className="text-primary">42 +</div>
              <div>43</div>
              <div>44</div>
            </div>

            <div className="space-y-8 md:space-y-10">
              <blockquote className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                “Before the harness, agent use was stuck at six engineers
                because nobody wanted to review a sprawling PR. When each run
                started from the same shared plan and returned file-level diffs
                with approval checkpoints, weekly adoption moved from single
                digits to 83% of engineering.”
              </blockquote>

              <figcaption className="border-l border-accent pl-5">
                <cite className="space-y-3 not-italic">
                  <span className="block font-body text-sm font-medium leading-6 text-foreground">
                    Mara Velez
                  </span>
                  <span className="block font-body text-sm font-normal leading-6 text-muted-foreground">
                    VP Engineering, Ternary Health
                  </span>
                  <span className="block font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    92-engineer product organization · TypeScript monorepo · 11
                    service repositories
                  </span>
                </cite>
              </figcaption>
            </div>
          </div>
        </figure>
      </div>
    </section>
  );
}
