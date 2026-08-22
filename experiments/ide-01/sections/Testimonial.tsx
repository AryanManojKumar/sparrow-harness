export default function Testimonial() {
  return (
    <section
      className="bg-muted py-20 text-foreground md:py-28 lg:py-32"
      aria-labelledby="testimonial-quote"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <figure className="mx-auto max-w-3xl space-y-8 md:space-y-10">
          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
            customer_review.md
          </p>

          <div className="grid grid-cols-[auto_1fr] gap-5 md:gap-8">
            <div
              className="border-r-2 border-primary font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground"
              aria-hidden="true"
            >
              <div className="space-y-3">
                <span className="block">118</span>
                <span className="block text-primary">+</span>
              </div>
            </div>

            <div className="space-y-8 md:space-y-10">
              <blockquote id="testimonial-quote">
                <p className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] md:text-2xl md:leading-8">
                  “Once every agent run had to map back to the shared plan and arrive
                  as a file-level diff, review stopped being archaeology. Across 31
                  changes, our median first-review time fell from 52 minutes to 18.”
                </p>
              </blockquote>

              <figcaption className="space-y-3">
                <p className="font-body text-base font-medium leading-7 md:text-lg md:leading-8">
                  Maya Chen
                </p>
                <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                  Principal Engineer, Northstar Ledger
                </p>
              </figcaption>
            </div>
          </div>
        </figure>
      </div>
    </section>
  );
}
