"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Cloud,
  Database,
  FileCheck2,
  LockKeyhole,
} from "lucide-react";

type StatusMarkProps = {
  delay: number;
  tone?: "verified" | "exception";
  reducedMotion: boolean;
};

function StatusMark({
  delay,
  tone = "verified",
  reducedMotion,
}: StatusMarkProps) {
  const Icon = tone === "exception" ? AlertTriangle : Check;

  return (
    <motion.span
      initial={reducedMotion ? false : { opacity: 0, scale: 0.85 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true, amount: 0.8 }}
      transition={{ duration: 0.18, delay }}
      className={`flex size-8 shrink-0 items-center justify-center rounded-full ${
        tone === "exception"
          ? "bg-accent text-foreground"
          : "bg-primary text-primary-foreground"
      }`}
    >
      <Icon className="size-5" aria-hidden="true" />
    </motion.span>
  );
}

type ChainSegmentProps = {
  delay: number;
  active?: boolean;
  reducedMotion: boolean;
};

function ChainSegment({
  delay,
  active = false,
  reducedMotion,
}: ChainSegmentProps) {
  return (
    <div className="h-px w-5 overflow-hidden bg-border md:w-8" aria-hidden="true">
      <motion.div
        className={`h-full w-full origin-left ${
          active ? "bg-accent" : "bg-primary"
        }`}
        initial={reducedMotion ? false : { scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true, amount: 0.8 }}
        transition={{ duration: 0.24, delay, ease: "easeOut" }}
      />
    </div>
  );
}

export default function Hero() {
  const prefersReducedMotion = useReducedMotion();
  const reducedMotion = Boolean(prefersReducedMotion);

  return (
    <section className="bg-background flex min-h-screen items-center overflow-hidden py-20 md:py-28 lg:py-32">
      <div className="mx-auto w-full max-w-7xl px-5 sm:px-8 lg:px-10">
        <div className="grid items-center gap-5 md:gap-8 lg:grid-cols-2">
          <motion.div
            initial={reducedMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="space-y-8 md:space-y-10"
          >
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Continuous SOC 2 compliance
              </p>
              <h1 className="font-display text-5xl font-semibold leading-[0.92] tracking-[-0.035em] text-foreground sm:text-6xl lg:text-7xl">
                SOC 2 evidence,
                <br />
                continuously ready.
              </h1>
            </div>

            <p className="max-w-xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Connect your cloud environment, monitor controls as infrastructure
              changes, and deliver audit-ready evidence without rebuilding the
              record at the end of every quarter.
            </p>

            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/demo"
                className="inline-flex rounded-md bg-primary px-5 py-3 font-body text-sm font-medium leading-6 text-primary-foreground shadow-[0_1px_2px_oklch(0.225_0.025_145/0.08)] transition-[box-shadow] duration-160 hover:shadow-[0_8px_20px_-14px_oklch(0.225_0.025_145/0.28)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Book a demo
                <ArrowRight className="size-5" aria-hidden="true" />
              </Link>
              <Link
                href="/docs"
                className="inline-flex rounded-md border border-border px-5 py-3 font-body text-sm font-medium leading-6 text-foreground transition-[box-shadow] duration-160 hover:shadow-[0_8px_20px_-14px_oklch(0.225_0.025_145/0.28)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Read the docs
              </Link>
            </div>
          </motion.div>

          <motion.div
            initial={reducedMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, delay: 0.08, ease: "easeOut" }}
            className="lg:w-[50vw]"
          >
            <div
              className="overflow-hidden rounded-md border border-border bg-card shadow-[0_1px_2px_oklch(0.225_0.025_145/0.08)]"
              role="img"
              aria-label="A continuous evidence chain connecting an AWS source to SOC 2 control CC6.1 and an audit-ready artifact"
            >
              <div className="flex items-center justify-between border-b border-border bg-muted p-5">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 items-center justify-center rounded-full border border-border bg-card text-primary">
                    <LockKeyhole className="size-5" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground">
                      Evidence chain
                    </p>
                    <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                      Production workspace
                    </p>
                  </div>
                </div>
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                  09:42 UTC
                </span>
              </div>

              <div className="space-y-8 p-5 sm:p-8">
                <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-2">
                  <div className="min-w-0 space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-primary">
                        <Cloud className="size-5" aria-hidden="true" />
                      </span>
                      <StatusMark
                        delay={0.08}
                        reducedMotion={reducedMotion}
                      />
                    </div>
                    <div>
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                        Source
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-foreground">
                        AWS IAM
                      </p>
                    </div>
                  </div>

                  <ChainSegment
                    delay={0}
                    reducedMotion={reducedMotion}
                  />

                  <div className="min-w-0 space-y-3">
                    <StatusMark delay={0.28} reducedMotion={reducedMotion} />
                    <div>
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                        CC6.1
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-foreground">
                        Access control
                      </p>
                    </div>
                  </div>

                  <ChainSegment
                    active
                    delay={0.24}
                    reducedMotion={reducedMotion}
                  />

                  <div className="min-w-0 space-y-3">
                    <StatusMark delay={0.52} reducedMotion={reducedMotion} />
                    <div>
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                        Artifact
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-foreground">
                        EVD-2048
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-5 md:grid-cols-2 md:gap-8">
                  <div className="rounded-md border border-border bg-muted p-5">
                    <div className="flex items-start gap-2">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-card text-primary">
                        <Database className="size-5" aria-hidden="true" />
                      </span>
                      <div className="space-y-3">
                        <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                          Captured evidence
                        </p>
                        <div>
                          <p className="font-body text-sm font-normal leading-6 text-foreground">
                            Credential report
                          </p>
                          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                            SHA256 verified · 09:42 UTC
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-md border border-border bg-card p-5">
                    <div className="flex items-start gap-2">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-primary">
                        <FileCheck2 className="size-5" aria-hidden="true" />
                      </span>
                      <div className="space-y-3">
                        <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                          Audit ready
                        </p>
                        <div>
                          <p className="font-body text-sm font-normal leading-6 text-foreground">
                            Owner, test, and source attached
                          </p>
                          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                            CSV · JSON · activity log
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between rounded-md border border-border bg-muted p-5">
                  <div className="flex items-center gap-2">
                    <StatusMark
                      tone="exception"
                      delay={0.7}
                      reducedMotion={reducedMotion}
                    />
                    <div>
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground">
                        CC7.2 · Exception
                      </p>
                      <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                        CloudTrail retention changed from 365 to 90 days
                      </p>
                    </div>
                  </div>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                    09:38 UTC
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
