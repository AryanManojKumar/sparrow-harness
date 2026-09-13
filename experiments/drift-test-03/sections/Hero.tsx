import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Check,
  Cloud,
  Database,
  FileCheck2,
  GitBranch,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";

const controlRows = [
  {
    id: "CC6.1",
    title: "Logical access",
    source: "AWS IAM",
    state: "Verified",
    selected: true,
  },
  {
    id: "CC6.6",
    title: "Network boundaries",
    source: "AWS VPC",
    state: "Verified",
    selected: false,
  },
  {
    id: "CC7.2",
    title: "System monitoring",
    source: "Datadog",
    state: "Verified",
    selected: false,
  },
  {
    id: "CC8.1",
    title: "Change management",
    source: "GitHub",
    state: "Verified",
    selected: false,
  },
];

const evidenceTape = [
  {
    control: "CC6.1",
    source: "AWS IAM",
    time: "09:42 UTC",
    state: "VERIFIED",
  },
  {
    control: "CC7.2",
    source: "DATADOG",
    time: "09:44 UTC",
    state: "VERIFIED",
  },
  {
    control: "CC8.1",
    source: "GITHUB",
    time: "09:47 UTC",
    state: "VERIFIED",
  },
];

export default function Hero() {
  return (
    <section className="bg-background overflow-hidden py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="grid items-center gap-6 md:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)] md:gap-8">
          <div className="space-y-8 md:space-y-10">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                SOC 2 / Continuous evidence collection
              </p>
              <h1 className="max-w-xl font-display text-5xl font-semibold leading-[0.94] tracking-[-0.025em] text-foreground md:text-7xl">
                SOC 2 evidence, continuously collected.
              </h1>
              <p className="max-w-xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
                Connect your cloud, identity, code, and monitoring systems.
                Controls are checked continuously and supporting evidence stays
                organized for the next audit—not assembled during it.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                asChild
                className="rounded-md bg-primary font-body text-base font-normal leading-7 text-primary-foreground shadow-xs transition-shadow duration-120 hover:bg-primary hover:shadow-sm focus-visible:ring-accent md:text-lg"
              >
                <Link href="/demo">
                  Book a demo
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="rounded-md border-border bg-transparent font-body text-base font-normal leading-7 text-primary shadow-xs transition-shadow duration-120 hover:bg-muted hover:text-primary hover:shadow-sm focus-visible:ring-accent md:text-lg"
              >
                <Link href="/docs">
                  <BookOpen aria-hidden="true" />
                  Read the docs
                </Link>
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
              <ShieldCheck
                aria-hidden="true"
                className="text-muted-foreground"
              />
              <p className="font-body text-sm font-normal leading-5 text-muted-foreground">
                Built for fintech teams that need inspectable control history
                and audit-ready provenance.
              </p>
            </div>
          </div>

          <figure className="md:w-[calc(100%+2rem)] xl:w-[calc(100%+(100vw-72rem)/2+2rem)]">
            <div className="overflow-hidden rounded-md border border-border bg-card shadow-xs">
              <div className="flex items-center justify-between gap-2 border-b border-border px-5 py-3 md:px-8">
                <div className="flex items-center gap-2">
                  <FileCheck2 aria-hidden="true" className="text-primary" />
                  <span className="font-body text-sm font-normal leading-5 text-foreground">
                    Control evidence
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 rounded-full bg-primary"
                  />
                  <span className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                    Collection active
                  </span>
                </div>
              </div>

              <div
                className="grid border-b border-border bg-accent md:grid-cols-3"
                aria-label="Continuous evidence tape"
              >
                {evidenceTape.map((item) => (
                  <div
                    key={item.control}
                    className="border-b border-foreground/20 px-5 py-3 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                        {item.control}
                      </span>
                      <Check aria-hidden="true" className="text-foreground" />
                    </div>
                    <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                      {item.source} · {item.time}
                    </p>
                    <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                      {item.state}
                    </p>
                  </div>
                ))}
              </div>

              <div className="grid md:grid-cols-[0.82fr_1.18fr]">
                <div className="border-b border-border bg-muted md:border-b-0 md:border-r">
                  <div className="border-b border-border px-5 py-3">
                    <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                      SOC 2 controls / 38 monitored
                    </p>
                  </div>

                  <div>
                    {controlRows.map((row) => (
                      <div
                        key={row.id}
                        className={`border-b border-border px-5 py-3 last:border-b-0 ${
                          row.selected
                            ? "border-l-2 border-l-accent bg-card"
                            : ""
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                              {row.id}
                            </p>
                            <p className="font-body text-sm font-normal leading-5 text-foreground">
                              {row.title}
                            </p>
                          </div>
                          <span
                            aria-label={row.state}
                            className="h-2 w-2 rounded-full bg-primary"
                          />
                        </div>
                        <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                          {row.source}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-3 px-5 py-6 md:px-8">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-3">
                      <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                        Selected proof / CC6.1
                      </p>
                      <h2 className="font-display text-2xl font-semibold leading-[1.1] tracking-[-0.01em] text-foreground md:text-3xl">
                        Administrative access requires MFA
                      </h2>
                    </div>
                    <ShieldCheck aria-hidden="true" className="text-primary" />
                  </div>

                  <p className="font-body text-sm font-normal leading-5 text-muted-foreground">
                    Collector compared active IAM administrators with the
                    enforced MFA policy and retained the source response.
                  </p>

                  <div className="border border-border bg-muted">
                    <div className="flex items-center gap-2 border-b border-border px-5 py-3">
                      <Cloud aria-hidden="true" className="text-primary" />
                      <span className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                        Source / AWS IAM
                      </span>
                    </div>
                    <div className="space-y-3 px-5 py-3">
                      <div className="flex items-center gap-2">
                        <Database
                          aria-hidden="true"
                          className="text-muted-foreground"
                        />
                        <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                          Collector / iam-credential-report
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <GitBranch
                          aria-hidden="true"
                          className="text-muted-foreground"
                        />
                        <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
                          Evidence hash / 8F2A-91CD-441E
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check aria-hidden="true" className="text-primary" />
                        <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-foreground">
                          Verified / 14 Aug 2026 · 09:42 UTC
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <figcaption className="pt-3 font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
              Exhibit 01 / Evidence lineage from source system to control
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
