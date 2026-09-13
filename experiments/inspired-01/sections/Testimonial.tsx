export default function Testimonial() {
  return (
    <section
      className="bg-muted py-20 md:py-28 lg:py-32"
      aria-label="Customer testimonial"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <figure className="max-w-4xl space-y-8 md:space-y-10">
          <blockquote>
            <p className="font-display text-2xl font-semibold leading-tight tracking-[-0.015em] md:text-3xl">
              “Continuous SOC 2 monitoring turned a six-week evidence chase
              into four days of review. Every control already had its source,
              timestamp, and audit-ready artifact attached.”
            </p>
          </blockquote>

          <figcaption className="space-y-3">
            <p className="font-body text-sm font-medium leading-6 text-foreground">
              Elena Park
            </p>
            <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
              VP of Security and Compliance, Arcway Payments
            </p>
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
