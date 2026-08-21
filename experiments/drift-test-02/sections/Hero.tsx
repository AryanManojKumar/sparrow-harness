"use client";

import { motion, type Variants } from "motion/react";
import {
  ArrowRight,
  Check,
  Cloud,
  FileCheck2,
  LockKeyhole,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const stagger: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const fadeUp: Variants = {
  hidden: {
    opacity: 0,
    y: 12,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0, 0, 0.2, 1],
    },
  },
};

const controls = [
  {
    name: "Cloud access reviews",
    detail: "AWS and GitHub evidence refreshed 8 minutes ago",
    state: "Passing",
  },
  {
    name: "Production change management",
    detail: "Deploy approvals linked to 42 changes",
    state: "Passing",
  },
  {
    name: "Vendor security reviews",
    detail: "One evidence request needs an owner",
    state: "Review",
  },
];

export default function Hero() {
  return (
    <section className="overflow-hidden bg-background py-24 md:py-32">
      <motion.div
        className="mx-auto grid max-w-6xl items-center gap-8 px-6 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        variants={stagger}
      >
        <motion.div className="space-y-8" variants={stagger}>
          <motion.div className="space-y-4" variants={stagger}>
            <motion.p
              className="text-xs font-medium uppercase tracking-widest text-primary"
              variants={fadeUp}
            >
              Continuous SOC 2 compliance
            </motion.p>

            <motion.h1
              className="text-5xl font-semibold leading-[1.05] tracking-tight text-foreground md:text-6xl"
              variants={fadeUp}
            >
              SOC 2 evidence, collected continuously.
            </motion.h1>

            <motion.p
              className="max-w-xl text-base leading-relaxed text-muted-foreground"
              variants={fadeUp}
            >
              Connect your cloud stack, monitor controls as they change, and
              keep audit-ready evidence current. Built for fintech teams that
              do not want compliance to become a quarterly fire drill.
            </motion.p>
          </motion.div>

          <motion.div
            className="flex flex-col gap-3 sm:flex-row"
            variants={fadeUp}
          >
            <Button
              asChild
              size="lg"
              className="rounded-lg bg-primary text-primary-foreground shadow-sm transition-colors duration-150 hover:bg-primary/90 hover:shadow-md"
            >
              <a href="/demo">
                Book a demo
                <ArrowRight aria-hidden="true" />
              </a>
            </Button>

            <Button
              asChild
              size="lg"
              variant="outline"
              className="rounded-lg border-border bg-background text-foreground shadow-sm transition-colors duration-150 hover:bg-muted hover:text-foreground hover:shadow-md"
            >
              <a href="/docs">Read the docs</a>
            </Button>
          </motion.div>

          <motion.div
            className="flex items-center gap-3 text-sm leading-normal text-muted-foreground"
            variants={fadeUp}
          >
            <LockKeyhole
              aria-hidden="true"
              className="text-primary"
              size={16}
              strokeWidth={1.5}
            />
            Read-only integrations with scoped permissions.
          </motion.div>
        </motion.div>

        <motion.figure className="md:-mr-8" variants={fadeUp}>
          <Card className="overflow-hidden rounded-lg border-border bg-card text-foreground shadow-md">
            <CardHeader className="border-b border-border">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-4">
                  <CardTitle className="text-xl font-medium leading-snug">
                    SOC 2 control room
                  </CardTitle>
                  <CardDescription className="text-sm leading-normal text-muted-foreground">
                    Production environment · Type II
                  </CardDescription>
                </div>

                <div className="flex items-center gap-3 text-sm leading-normal text-primary">
                  <Check aria-hidden="true" size={16} strokeWidth={1.5} />
                  Monitoring
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-8">
              <div className="grid gap-8 sm:grid-cols-3">
                <div className="space-y-4">
                  <FileCheck2
                    aria-hidden="true"
                    className="text-primary"
                    size={20}
                    strokeWidth={1.5}
                  />
                  <div>
                    <p className="text-xl font-medium leading-snug">47</p>
                    <p className="text-sm leading-normal text-muted-foreground">
                      Controls monitored
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <Cloud
                    aria-hidden="true"
                    className="text-primary"
                    size={20}
                    strokeWidth={1.5}
                  />
                  <div>
                    <p className="text-xl font-medium leading-snug">12</p>
                    <p className="text-sm leading-normal text-muted-foreground">
                      Connected systems
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <Check
                    aria-hidden="true"
                    className="text-primary"
                    size={20}
                    strokeWidth={1.5}
                  />
                  <div>
                    <p className="text-xl font-medium leading-snug">184</p>
                    <p className="text-sm leading-normal text-muted-foreground">
                      Evidence items
                    </p>
                  </div>
                </div>
              </div>

              <div className="overflow-hidden rounded-lg border border-border">
                {controls.map((control) => (
                  <div
                    key={control.name}
                    className="flex items-center justify-between gap-3 border-b border-border px-6 last:border-b-0"
                  >
                    <div className="space-y-4">
                      <p className="text-sm font-medium leading-normal text-foreground">
                        {control.name}
                      </p>
                      <p className="text-xs leading-normal text-muted-foreground">
                        {control.detail}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                      <span
                        aria-hidden="true"
                        className={
                          control.state === "Review"
                            ? "h-3 w-3 bg-accent"
                            : "h-3 w-3 bg-primary"
                        }
                      />
                      {control.state}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between gap-3 border-t border-border">
                <p className="text-sm leading-normal text-muted-foreground">
                  Evidence package updated today
                </p>
                <p className="text-sm font-medium leading-normal text-primary">
                  Audit ready
                </p>
              </div>
            </CardContent>
          </Card>

          <figcaption className="sr-only">
            SOC 2 compliance dashboard showing continuously monitored controls,
            connected systems, and audit evidence.
          </figcaption>
        </motion.figure>
      </motion.div>
    </section>
  );
}
