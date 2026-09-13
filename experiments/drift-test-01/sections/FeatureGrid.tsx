"use client";

import { motion } from "motion/react";
import {
  Plug,
  Radar,
  FileCheck2,
  GitPullRequestArrow,
  BellRing,
  Users,
  type LucideIcon,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  body: string;
};

const features: Feature[] = [
  {
    icon: Plug,
    title: "Read-only infrastructure access",
    body: "Connect AWS, GCP, Azure, GitHub and your identity provider with scoped read-only roles. No agents on your hosts, no write permissions, no exceptions.",
  },
  {
    icon: Radar,
    title: "Continuous control monitoring",
    body: "Every SOC 2 control is checked on a schedule measured in hours, not quarters. You see the state of your environment as it is now, not as it was at the last screenshot.",
  },
  {
    icon: FileCheck2,
    title: "Evidence an auditor accepts",
    body: "Each check writes a timestamped, immutable record with the raw API response behind it. Export the full package or give your auditor scoped access directly.",
  },
  {
    icon: GitPullRequestArrow,
    title: "Change-aware drift detection",
    body: "A control that passed last week and fails today is tied back to the deploy, IAM edit or config change that broke it. You get the diff, not just the red mark.",
  },
  {
    icon: BellRing,
    title: "Alerts with a threshold you set",
    body: "Route failures to Slack, PagerDuty or a webhook. Severity and quiet hours are yours to define, so compliance noise stays out of your on-call rotation.",
  },
  {
    icon: Users,
    title: "Access reviews and onboarding",
    body: "Personnel, device posture and policy acknowledgements track against your HR system. Joiner and leaver evidence is collected as it happens.",
  },
];

export default function FeatureGrid() {
  return (
    <section className="bg-background py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="max-w-2xl space-y-4"
        >
          <p className="flex items-center gap-3 text-xs font-medium tracking-widest uppercase text-muted-foreground">
            <span aria-hidden className="h-px w-8 bg-accent" />
            What Ledgerline does
          </p>
          <h2 className="text-3xl leading-tight font-semibold md:text-4xl">
            Compliance that reads your infrastructure, not your intentions
          </h2>
          <p className="text-base leading-relaxed text-muted-foreground">
            SOC 2 fails in the gap between the policy you wrote and the systems
            you actually run. Ledgerline closes that gap by checking the systems
            themselves, on a schedule, and keeping the receipts.
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.article
                key={feature.title}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{
                  duration: 0.4,
                  ease: "easeOut",
                  delay: index * 0.06,
                }}
                className="flex flex-col space-y-4 rounded-lg border border-border bg-card p-8 shadow-sm transition-colors duration-150 hover:border-primary/40 hover:shadow-md"
              >
                <Icon
                  aria-hidden
                  strokeWidth={1.5}
                  className="h-6 w-6 shrink-0 text-primary"
                />
                <h3 className="text-xl leading-snug font-medium">
                  {feature.title}
                </h3>
                <p className="text-sm leading-normal text-muted-foreground">
                  {feature.body}
                </p>
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
