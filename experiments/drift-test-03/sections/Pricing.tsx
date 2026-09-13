import { Check } from "lucide-react";

const tiers = [
  {
    name: "Foundation",
    price: "$1,500",
    cadence: "per month, billed annually",
    summary:
      "For fintech teams establishing continuous SOC 2 monitoring before their next audit cycle.",
    features: [
      "AWS or Google Cloud connection",
      "Continuous control monitoring",
      "Automated evidence collection",
      "One SOC 2 framework workspace",
      "Auditor-ready evidence exports",
    ],
    cta: "Book a Foundation demo",
  },
  {
    name: "Scale",
    price: "$2,750",
    cadence: "per month, billed annually",
    summary:
      "For growing compliance teams managing more systems, owners, and evidence across the business.",
    features: [
      "AWS, Google Cloud, and Azure",
      "Continuous control monitoring",
      "Automated evidence collection",
      "GitHub and identity integrations",
      "Control owner workflows",
      "Auditor workspace and exports",
    ],
    cta: "Book a Scale demo",
    recommended: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "annual agreement",
    summary:
      "For multi-entity fintech companies with custom controls, complex infrastructure, or dedicated audit programs.",
    features: [
      "Unlimited cloud environments",
      "Custom control mappings",
      "Multiple entities and workspaces",
      "Evidence retention policies",
      "SSO and role-based access",
      "Implementation support",
      "Security review assistance",
    ],
    cta: "Discuss Enterprise",
  },
];

export default function Pricing() {
  return (
    <section
      className="bg-background py-20 md:py-28"
      aria-labelledby="pricing-heading"
    >
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="space-y-8 md:space-y-10">
          <header className="space-y-3">
            <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
              SOC 2 / Service plans
            </p>
            <h2
              id="pricing-heading"
              className="font-display text-4xl font-semibold leading-none tracking-[-0.02em] text-foreground md:text-5xl"
            >
              Pricing that follows your control environment.
            </h2>
            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
              Every plan includes continuous SOC 2 monitoring and audit-ready
              evidence. Choose based on infrastructure scope and operating
              complexity, not control count.
            </p>
          </header>

          <div className="grid items-stretch gap-6 md:grid-cols-3 md:gap-8">
            {tiers.map((tier) => (
              <article
                key={tier.name}
                className="flex h-full flex-col rounded-md border border-border bg-card p-6 shadow-xs md:p-8"
              >
                <div className="space-y-8">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-display text-2xl font-semibold leading-[1.1] tracking-[-0.01em] text-foreground md:text-3xl">
                        {tier.name}
                      </h3>
                      {tier.recommended ? (
                        <span className="rounded-sm bg-accent px-3 py-2 font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                          Recommended
                        </span>
                      ) : null}
                    </div>

                    <div className="space-y-3">
                      <p className="font-display text-4xl font-semibold leading-none tracking-[-0.02em] text-foreground md:text-5xl">
                        {tier.price}
                      </p>
                      <p className="font-body text-sm font-normal leading-5 text-muted-foreground">
                        {tier.cadence}
                      </p>
                    </div>

                    <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
                      {tier.summary}
                    </p>
                  </div>

                  <ul className="space-y-3" aria-label={`${tier.name} features`}>
                    {tier.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-2 font-body text-sm font-normal leading-5 text-foreground"
                      >
                        <Check
                          aria-hidden="true"
                          className="mt-1 h-4 w-4 shrink-0 text-primary"
                          strokeWidth={2}
                        />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-auto pt-8">
                  <a
                    href="#book-demo"
                    className="flex w-full items-center justify-center rounded-md bg-primary px-5 py-3 font-body text-base font-normal leading-7 text-primary-foreground shadow-xs transition-shadow duration-[120ms] hover:shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary md:text-lg"
                  >
                    {tier.cta}
                  </a>
                </div>
              </article>
            ))}
          </div>

          <p className="font-body text-sm font-normal leading-5 text-muted-foreground">
            All prices exclude applicable taxes. Implementation scope and data
            retention requirements are confirmed before contracting.
          </p>
        </div>
      </div>
    </section>
  );
}
