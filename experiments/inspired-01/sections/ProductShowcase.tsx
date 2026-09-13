"use client";

import { motion, useReducedMotion } from "motion/react";
import {
  Cloud,
  FileCheck2,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";

const chainStages = [
  {
    eyebrow: "SOURCE SYSTEM",
    title: "AWS IAM",
    detail: "Organization snapshot",
    metadata: "2026-08-22 14:32:08 UTC",
    icon: Cloud,
    state: "Collected",
    exception: false,
  },
  {
    eyebrow: "CONTROL",
    title: "CC6.1 / IAM-04",
    detail: "Privileged access requires MFA",
    metadata: "Evaluated against 42 principals",
    icon: ShieldCheck,
    state: "Monitored",
    exception: false,
  },
  {
    eyebrow: "EXCEPTION",
    title: "EXC-0217",
    detail: "Break-glass role MFA exemption",
    metadata: "Owner attestation attached",
    icon: TriangleAlert,
    state: "Accepted",
    exception: true,
  },
  {
    eyebrow: "ARTIFACT",
    title: "EV-2026-1842",
    detail: "Access control evidence packet",
    metadata: "Hash sealed · Audit-ready",
    icon: FileCheck2,
    state: "Ready",
    exception: false,
  },
];

export default function ProductShowcase() {
  const reduceMotion = useReducedMotion();

  return (
    <section
      className="bg-background py-20 md:py-28 lg:py-32"
      aria-labelledby="product-showcase-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8 lg:px-10">
        <div className="space-y-8 md:space-y-10">
          <div className="grid gap-5 md:grid-cols-12 md:gap-8">
            <div className="space-y-3 md:col-span-7">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                CONTROL MONITORING
              </p>
              <h2
                id="product-showcase-heading"
                className="font-display text-4xl font-semibold leading-none tracking-[-0.025em] text-foreground md:text-5xl"
              >
                Every SOC 2 control keeps its evidence trail.
              </h2>
            </div>

            <div className="md:col-span-5 md:self-end">
              <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Infrastructure state is collected, evaluated, and bound to the
                exact control, exception record, and artifact an auditor will
                review.
              </p>
            </div>
          </div>

          <figure className="space-y-3">
            <div className="overflow-hidden rounded-md border border-border bg-card shadow-[0_1px_2px_oklch(0.225_0.025_145/0.08)]">
              <div className="flex flex-col gap-5 border-b border-border bg-muted p-5 sm:flex-row sm:items-center sm:justify-between sm:p-8">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full bg-primary"
                      aria-hidden="true"
                    />
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                      CONTINUOUS MONITOR
                    </p>
                  </div>
                  <p className="font-display text-2xl font-semibold leading-tight tracking-[-0.015em] text-foreground md:text-3xl">
                    Privileged access evidence chain
                  </p>
                </div>

                <div className="space-y-3 sm:text-right">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    AWS ORGANIZATIONS · PRODUCTION
                  </p>
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground">
                    LAST EVALUATED 14:32:11 UTC
                  </p>
                </div>
              </div>

              <div className="p-5 sm:p-8 lg:p-10">
                <div className="relative">
                  <div
                    className="absolute bottom-5 left-5 top-5 w-px bg-border md:hidden"
                    aria-hidden="true"
                  >
                    <motion.div
                      className="h-full w-px origin-top bg-primary"
                      initial={reduceMotion ? false : { scaleY: 0 }}
                      whileInView={{ scaleY: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.24, ease: "easeOut" }}
                    />
                  </div>

                  <div
                    className="absolute left-[12.5%] right-[12.5%] top-5 hidden h-px md:flex"
                    aria-hidden="true"
                  >
                    {[false, true, false].map((active, index) => (
                      <motion.span
                        key={index}
                        className={`h-px flex-1 origin-left ${
                          active ? "bg-accent" : "bg-primary"
                        }`}
                        initial={reduceMotion ? false : { scaleX: 0 }}
                        whileInView={{ scaleX: 1 }}
                        viewport={{ once: true }}
                        transition={{
                          duration: 0.24,
                          delay: index * 0.08,
                          ease: "easeOut",
                        }}
                      />
                    ))}
                  </div>

                  <div className="relative grid gap-5 md:grid-cols-4 md:gap-8">
                    {chainStages.map((stage, index) => {
                      const Icon = stage.icon;

                      return (
                        <div
                          key={stage.title}
                          className={`relative rounded-md border bg-card p-5 ${
                            stage.exception
                              ? "border-accent"
                              : "border-border"
                          }`}
                        >
                          <div className="space-y-8">
                            <div className="flex items-center justify-between gap-2">
                              <motion.div
                                className={`relative flex h-10 w-10 items-center justify-center rounded-full border ${
                                  stage.exception
                                    ? "border-accent bg-accent text-foreground"
                                    : "border-border bg-muted text-primary"
                                }`}
                                initial={
                                  reduceMotion
                                    ? false
                                    : { opacity: 0, scale: 0.9 }
                                }
                                whileInView={{ opacity: 1, scale: 1 }}
                                viewport={{ once: true }}
                                transition={{
                                  duration: 0.18,
                                  delay: index * 0.08,
                                  ease: "easeOut",
                                }}
                              >
                                <Icon className="h-5 w-5" aria-hidden="true" />
                              </motion.div>

                              <span
                                className={`rounded-md border px-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] ${
                                  stage.exception
                                    ? "border-accent text-foreground"
                                    : "border-border text-primary"
                                }`}
                              >
                                {stage.state}
                              </span>
                            </div>

                            <div className="space-y-3">
                              <p
                                className={`font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] ${
                                  stage.exception
                                    ? "text-foreground"
                                    : "text-muted-foreground"
                                }`}
                              >
                                {stage.eyebrow}
                              </p>
                              <p className="font-mono text-sm font-normal leading-6 text-foreground">
                                {stage.title}
                              </p>
                              <p className="font-body text-sm font-normal leading-6 text-foreground">
                                {stage.detail}
                              </p>
                              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                                {stage.metadata}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="grid gap-5 border-t border-border bg-muted p-5 sm:grid-cols-2 sm:p-8 md:gap-8">
                <div className="space-y-3">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    EVIDENCE INTEGRITY
                  </p>
                  <p className="font-body text-sm font-normal leading-6 text-foreground">
                    Source payload, evaluation result, exception approval, and
                    exported artifact share one immutable evidence ID.
                  </p>
                </div>

                <div className="space-y-3 sm:text-right">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    ARTIFACT DESTINATION
                  </p>
                  <p className="font-mono text-sm font-normal leading-6 text-foreground">
                    SOC2-2026 / CC6.1 / EV-2026-1842
                  </p>
                </div>
              </div>
            </div>

            <figcaption className="font-body text-sm font-normal leading-6 text-muted-foreground">
              A live control record showing the source snapshot, SOC 2 mapping,
              retained exception, and sealed audit artifact as one reviewable
              chain.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
