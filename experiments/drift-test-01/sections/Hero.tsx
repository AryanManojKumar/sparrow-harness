"use client";

import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

const rise = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

const transition = { duration: 0.4, ease: "easeOut" } as const;

const controls = [
  { id: "CC6.1", name: "Logical access reviews", state: "Evidence current" },
  { id: "CC6.6", name: "MFA enforced on cloud console", state: "Evidence current" },
  { id: "CC7.2", name: "Infrastructure log monitoring", state: "Drift detected", drift: true },
  { id: "CC8.1", name: "Change management approvals", state: "Evidence current" },
];

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-background py-24 md:py-32">
      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-8 px-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <motion.div
          initial="hidden"
          animate="visible"
          transition={{ staggerChildren: 0.06 }}
          className="max-w-xl space-y-8"
        >
          <motion.p
            variants={rise}
            transition={transition}
            className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
          >
            Continuous SOC 2 compliance
          </motion.p>

          <div className="space-y-4">
            <motion.h1
              variants={rise}
              transition={transition}
              className="text-5xl leading-[1.05] tracking-tight md:text-6xl"
            >
              Audit-ready between audits.
            </motion.h1>

            <motion.p
              variants={rise}
              transition={transition}
              className="text-base leading-relaxed text-muted-foreground"
            >
              Ledgerline connects to your cloud accounts, watches your SOC 2 controls
              continuously, and collects the evidence as it happens. Your auditor gets a
              dated trail instead of a folder of screenshots taken the week before
              fieldwork.
            </motion.p>
          </div>

          <motion.div
            variants={rise}
            transition={transition}
            className="flex flex-wrap items-center gap-4"
          >
            <Button asChild size="lg" className="h-11 px-5 text-base transition-colors duration-150">
              <a href="/demo">Book a demo</a>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="h-11 px-5 text-base transition-colors duration-150"
            >
              <a href="/docs">
                Read the docs
                <ArrowRight aria-hidden="true" />
              </a>
            </Button>
          </motion.div>

          <motion.p
            variants={rise}
            transition={transition}
            className="text-sm leading-normal text-muted-foreground"
          >
            Read-only access. Connects to AWS, GCP and Azure. Type II evidence from the
            first day you turn it on.
          </motion.p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transition, delay: 0.24 }}
          className="lg:-mr-24 xl:-mr-32"
        >
          <div className="rounded-lg border border-border bg-card p-6 shadow-md">
            <div className="flex items-baseline justify-between border-b border-border pb-4">
              <p className="text-sm font-medium leading-normal text-foreground">
                Control monitor
              </p>
              <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                SOC 2 Type II
              </p>
            </div>

            <ul className="divide-y divide-border">
              {controls.map((control) => (
                <li
                  key={control.id}
                  className="flex items-center justify-between gap-8 py-4"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm leading-normal text-foreground">
                      {control.name}
                    </p>
                    <p className="text-xs leading-normal text-muted-foreground">
                      {control.id}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span
                      aria-hidden="true"
                      className={
                        control.drift
                          ? "size-1.5 rounded-full bg-accent"
                          : "size-1.5 rounded-full bg-primary"
                      }
                    />
                    <span className="text-xs leading-normal text-muted-foreground">
                      {control.state}
                    </span>
                  </div>
                </li>
              ))}
            </ul>

            <div className="border-t border-border pt-4">
              <p className="text-xs leading-normal text-muted-foreground">
                61 controls monitored &middot; 1,428 evidence records collected this quarter
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
