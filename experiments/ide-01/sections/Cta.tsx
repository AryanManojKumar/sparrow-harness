import { Button } from "@/components/ui/button";

export default function Cta() {
  return (
    <section className="bg-muted py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid grid-cols-1 gap-5 text-center md:grid-cols-12 md:gap-8">
          <div className="space-y-8 md:col-span-8 md:col-start-3 md:space-y-10">
            <div className="space-y-3">
              <h2 className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl">
                Make the next agent change reviewable.
              </h2>
              <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Start with a shared plan. Every run returns a file-level diff for
                an engineer to inspect before it lands.
              </p>
            </div>

            <Button
              asChild
              size="lg"
              className="rounded-md border border-border bg-accent font-body text-sm font-medium text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:bg-accent hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)]"
            >
              <a href="/signup">Start free</a>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
