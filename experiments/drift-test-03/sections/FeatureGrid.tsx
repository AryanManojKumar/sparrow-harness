import type { LucideIcon } from "lucide-react";
import {
  BellRing,
  CloudCog,
  FileCheck2,
  GitBranch,
  ListChecks,
  ShieldCheck,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  body: string;
};

const features: Feature[] = [
  {
    icon: CloudCog,
    title: "Connect infrastructure once",
    body: "Read-only collectors map AWS, GitHub, identity, and deployment data to the controls they support.",
  },
  {
    icon: ListChecks,
    title: "Monitor controls continuously",
    body: "Automated tests check control operation on schedule, without waiting for the next audit request list.",
  },
  {
    icon: FileCheck2,
    title: "Collect audit-ready evidence",
    body: "Every artifact includes its source, collection time, control mapping, and verification state.",
  },
  {
    icon: GitBranch,
    title: "Preserve evidence lineage",
    body: "Chain-of-custody records show how evidence was collected, evaluated, and attached to each control.",
  },
  {
    icon: BellRing,
    title: "Route control drift",
    body: "Failed checks reach the responsible owner with the affected resource and the evidence needed to resolve them.",
  },
  {
    icon: ShieldCheck,
    title: "Give auditors a clean record",
    body: "Share scoped evidence and control history in one workspace instead of rebuilding the audit trail from tickets.",
  },
];

export default function FeatureGrid() {
  return (
    <section className="bg-muted py-20 md:py-28" aria-labelledby="feature-grid-heading">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="space-y-8 md:space-y-10">
          <header className="space-y-3">
            <p className="font-mono text-xs font-medium leading-4 tracking-[0.08em] uppercase text-muted-foreground">
              SOC 2 / Continuous control monitoring
            </p>
            <h2
              id="feature-grid-heading"
              className="font-display text-4xl font-semibold leading-none tracking-[-0.02em] text-foreground md:text-5xl"
            >
              Controls that stay ready between audits.
            </h2>
            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
              Maintain a current SOC 2 record from the systems where controls
              actually operate. Collection, verification, ownership, and
              auditor access remain traceable in one place.
            </p>
          </header>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 md:gap-8 lg:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <article
                  key={feature.title}
                  className="h-full rounded-md border border-border bg-card p-6 shadow-xs transition-shadow duration-[120ms] hover:shadow-sm md:p-8"
                >
                  <div className="space-y-3">
                    <Icon
                      aria-hidden="true"
                      className="text-primary"
                      size={24}
                      strokeWidth={1.75}
                    />
                    <h3 className="font-display text-2xl font-semibold leading-[1.1] tracking-[-0.01em] text-foreground md:text-3xl">
                      {feature.title}
                    </h3>
                    <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
                      {feature.body}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
