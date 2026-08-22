import { Button } from "@/components/ui/button";

export default function Cta() {
  return (
    <section
      aria-labelledby="cta-heading"
      className="bg-background py-20 md:py-28 lg:py-32"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-3xl space-y-8 text-center">
          <h2
            id="cta-heading"
            className="font-display text-4xl font-semibold leading-none tracking-[-0.025em] md:text-5xl"
          >
            Make your next SOC 2 audit a handoff, not a project.
          </h2>
          <p className="mx-auto max-w-2xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
            See how continuous control monitoring turns cloud activity into
            current, audit-ready evidence.
          </p>
          <Button asChild>
            <a href="/demo">Book a demo</a>
          </Button>
        </div>
      </div>
    </section>
  );
}
