import {
  CloudCog,
  FileCheck2,
  GitPullRequest,
  ListChecks,
  RefreshCw,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  category: string;
  title: string;
  body: string;
};

const features: Feature[] = [
  {
    icon: CloudCog,
    category: "Infrastructure sources",
    title: "Connect the systems that hold the evidence",
    body: "Collect configuration and access data from AWS, GCP, identity providers, code hosts, and other systems in your control environment.",
  },
  {
    icon: RefreshCw,
    category: "Control monitoring",
    title: "Test controls continuously",
    body: "Evaluate SOC 2 controls against current infrastructure state instead of relying on screenshots and point-in-time checks.",
  },
  {
    icon: TriangleAlert,
    category: "Exception handling",
    title: "See drift while it is still manageable",
    body: "Flag failed checks with the affected control, source, timestamp, and remediation context needed to investigate the change.",
  },
  {
    icon: GitPullRequest,
    category: "Change context",
    title: "Trace exceptions back to a change",
    body: "Link control failures to deployments, configuration updates, and access changes so engineering can resolve the underlying cause.",
  },
  {
    icon: ListChecks,
    category: "Evidence mapping",
    title: "Keep every artifact tied to its control",
    body: "Maintain a clear chain from control ID to source record, collection time, review status, and retained audit evidence.",
  },
  {
    icon: FileCheck2,
    category: "Audit handoff",
    title: "Export a reviewable evidence packet",
    body: "Produce organized, audit-ready records with control mappings and timestamps, without rebuilding the quarter from scattered files.",
  },
];

export default function FeatureGrid() {
  return (
    <section
      className="bg-muted py-20 md:py-28 lg:py-32"
      aria-labelledby="feature-grid-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <div className="space-y-8 md:space-y-10">
          <div className="grid gap-5 md:grid-cols-2 md:gap-8">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Control monitoring
              </p>
              <h2
                id="feature-grid-heading"
                className="font-display text-4xl font-semibold leading-none tracking-[-0.025em] text-foreground md:text-5xl"
              >
                The controls stay live between audits.
              </h2>
            </div>

            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Replace periodic evidence hunts with a continuous record of what
              was checked, where the result came from, and whether each SOC 2
              control is operating as expected.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 md:gap-8 lg:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <article
                  key={feature.title}
                  className="rounded-md border border-border bg-card p-5 shadow-[0_1px_2px_oklch(0.225_0.025_145/0.08)] transition-shadow duration-[160ms] hover:shadow-[0_8px_20px_-14px_oklch(0.225_0.025_145/0.28)] md:p-8"
                >
                  <div className="space-y-8">
                    <div className="flex items-center gap-2">
                      <Icon
                        aria-hidden="true"
                        size={20}
                        strokeWidth={1.75}
                        className="shrink-0 text-primary"
                      />
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                        {feature.category}
                      </p>
                    </div>

                    <div className="space-y-3">
                      <h3 className="font-display text-2xl font-semibold leading-tight tracking-[-0.015em] text-foreground md:text-3xl">
                        {feature.title}
                      </h3>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        {feature.body}
                      </p>
                    </div>
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
