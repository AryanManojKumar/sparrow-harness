"use client";

import { motion, useReducedMotion } from "motion/react";
import {
  AlertTriangle,
  Check,
  Cloud,
  FileText,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

type EvidenceEvent = {
  label: string;
  title: string;
  detail: string;
  timestamp: string;
  icon: LucideIcon;
  state: "verified" | "exception" | "artifact";
};

const steps = [
  {
    number: "01",
    title: "Connect the source",
    description:
      "Read-only integrations collect configuration and identity data directly from your cloud environment.",
  },
  {
    number: "02",
    title: "Evaluate the control",
    description:
      "Each observation is tested against the mapped SOC 2 control and retained with its source context.",
  },
  {
    number: "03",
    title: "Track the exception",
    description:
      "Owners see the failing resource, expected state, and remediation history without opening a separate evidence request.",
  },
  {
    number: "04",
    title: "Produce the artifact",
    description:
      "Once the control passes, the complete evidence chain is packaged for the auditor with timestamps intact.",
  },
];

const evidenceEvents: EvidenceEvent[] = [
  {
    label: "SOURCE · AWS ORGANIZATIONS",
    title: "IAM account configuration collected",
    detail: "Account 4821-9034-1172 · read-only connector",
    timestamp: "14:31:42 UTC",
    icon: Cloud,
    state: "verified",
  },
  {
    label: "CONTROL · CC6.1",
    title: "Root account MFA exception detected",
    detail: "Expected: hardware or virtual MFA enabled",
    timestamp: "14:31:44 UTC",
    icon: AlertTriangle,
    state: "exception",
  },
  {
    label: "VERIFICATION · CC6.1",
    title: "Configuration re-evaluated and passed",
    detail: "Root account MFA device present",
    timestamp: "14:32:18 UTC",
    icon: ShieldCheck,
    state: "verified",
  },
  {
    label: "ARTIFACT · EV-CC6.1-0842",
    title: "Audit-ready evidence sealed",
    detail: "Source snapshot, test result, and remediation history",
    timestamp: "14:32:20 UTC",
    icon: FileText,
    state: "artifact",
  },
];

export default function FeatureDetail() {
  const reduceMotion = useReducedMotion();

  const reveal = {
    initial: reduceMotion ? false : { opacity: 0, y: 6 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.3 },
    transition: { duration: reduceMotion ? 0 : 0.18 },
  };

  return (
    <section className="bg-background py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <div className="grid items-center gap-5 md:gap-8 lg:grid-cols-[0.8fr_1.2fr]">
          <motion.div {...reveal} className="space-y-8 md:space-y-10">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Evidence production
              </p>
              <h2 className="font-display text-4xl font-semibold leading-none tracking-[-0.025em] text-foreground md:text-5xl">
                Trace every control back to the system that proves it.
              </h2>
              <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Continuous collection turns each SOC 2 control into a reviewable
                chain of source data, test results, exceptions, and final
                evidence—without relying on screenshots assembled at audit time.
              </p>
            </div>

            <ol className="space-y-3" aria-label="Continuous evidence workflow">
              {steps.map((step) => (
                <li
                  key={step.number}
                  className="grid grid-cols-[auto_1fr] gap-5 border-t border-border pt-3"
                >
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    {step.number}
                  </span>
                  <div className="space-y-3">
                    <h3 className="font-body text-sm font-medium leading-6 text-foreground">
                      {step.title}
                    </h3>
                    <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </motion.div>

          <motion.figure
            {...reveal}
            className="overflow-hidden rounded-md border border-border bg-card shadow-[0_1px_2px_oklch(0.225_0.025_145/0.08)] transition-shadow duration-[160ms] hover:shadow-[0_8px_20px_-14px_oklch(0.225_0.025_145/0.28)]"
            aria-label="Evidence chain for SOC 2 control CC6.1"
          >
            <div className="flex items-start justify-between gap-2 border-b border-border bg-muted p-5 md:p-8">
              <div className="space-y-3">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                  Control record
                </p>
                <h3 className="font-display text-2xl font-semibold leading-tight tracking-[-0.015em] text-foreground md:text-3xl">
                  CC6.1 · Logical access
                </h3>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-primary bg-card px-3 py-3 text-primary">
                <Check className="size-5" aria-hidden="true" />
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em]">
                  Verified
                </span>
              </div>
            </div>

            <div className="space-y-8 p-5 md:p-8">
              <div className="grid gap-5 border-b border-border pb-3 md:grid-cols-3 md:gap-8">
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    Framework
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-foreground">
                    SOC 2 · Security
                  </p>
                </div>
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    Test cadence
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-foreground">
                    Every 15 minutes
                  </p>
                </div>
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    Last evaluated
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-foreground">
                    2026-08-22
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground">
                  Continuous evidence chain
                </p>

                <div>
                  {evidenceEvents.map((event, index) => {
                    const Icon = event.icon;
                    const isLast = index === evidenceEvents.length - 1;
                    const isException = event.state === "exception";

                    return (
                      <div
                        key={event.label}
                        className="grid grid-cols-[auto_1fr] gap-5"
                      >
                        <div className="flex flex-col items-center gap-2">
                          <motion.div
                            initial={
                              reduceMotion
                                ? false
                                : { opacity: 0, scale: 0.85 }
                            }
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true, amount: 0.5 }}
                            transition={{
                              duration: reduceMotion ? 0 : 0.18,
                              delay: reduceMotion ? 0 : index * 0.06,
                            }}
                            className={
                              isException
                                ? "flex size-8 items-center justify-center rounded-full border border-accent bg-accent text-foreground"
                                : "flex size-8 items-center justify-center rounded-full border border-primary bg-primary text-primary-foreground"
                            }
                          >
                            <Icon className="size-5" aria-hidden="true" />
                          </motion.div>

                          {!isLast && (
                            <motion.div
                              initial={
                                reduceMotion ? false : { scaleY: 0 }
                              }
                              whileInView={{ scaleY: 1 }}
                              viewport={{ once: true, amount: 0.5 }}
                              transition={{
                                duration: reduceMotion ? 0 : 0.24,
                                delay: reduceMotion ? 0 : index * 0.06,
                              }}
                              className={
                                isException
                                  ? "w-px flex-1 origin-top bg-accent"
                                  : "w-px flex-1 origin-top bg-border"
                              }
                            />
                          )}
                        </div>

                        <div className="space-y-3 pb-8">
                          <div className="rounded-md border border-border bg-muted p-3">
                            <div className="flex items-start justify-between gap-2">
                              <p
                                className={
                                  isException
                                    ? "font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground"
                                    : "font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground"
                                }
                              >
                                {event.label}
                              </p>
                              <time className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                                {event.timestamp}
                              </time>
                            </div>
                            <div className="space-y-3 pt-3">
                              <p className="font-body text-sm font-medium leading-6 text-foreground">
                                {event.title}
                              </p>
                              <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                                {event.detail}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <figcaption className="sr-only">
              A source-to-artifact record showing an AWS configuration
              observation, a control exception, its verification, and the
              resulting audit-ready evidence.
            </figcaption>
          </motion.figure>
        </div>
      </div>
    </section>
  );
}
