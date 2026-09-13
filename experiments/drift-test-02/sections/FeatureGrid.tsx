"use client";

import { motion, type Variants } from "motion/react";
import {
  Activity,
  BellRing,
  CloudCog,
  FileCheck2,
  ListChecks,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  body: string;
};

const features: Feature[] = [
  {
    icon: CloudCog,
    title: "Read-only infrastructure access",
    body: "Connect AWS, GitHub, identity, and production systems without placing an agent in your environment.",
  },
  {
    icon: Activity,
    title: "Continuous control monitoring",
    body: "Evaluate control state as systems change, rather than reconstructing compliance at the end of each quarter.",
  },
  {
    icon: FileCheck2,
    title: "Evidence collected automatically",
    body: "Capture configuration, access, and operational records with timestamps and source context intact.",
  },
  {
    icon: ListChecks,
    title: "Evidence mapped to controls",
    body: "Link each artifact to the relevant SOC 2 control so reviewers can trace claims back to source systems.",
  },
  {
    icon: BellRing,
    title: "Actionable exceptions",
    body: "Route failed checks to the right owner with the affected resource, expected state, and remediation context.",
  },
  {
    icon: ShieldCheck,
    title: "An audit-ready workspace",
    body: "Give auditors a structured view of controls, evidence, exceptions, and remediation history without spreadsheet handoffs.",
  },
];

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: "easeOut",
    },
  },
};

const staggeredGrid: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
    },
  },
};

export default function FeatureGrid() {
  return (
    <section
      className="bg-muted py-24 md:py-32"
      aria-labelledby="feature-grid-heading"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="space-y-8">
          <motion.div
            className="grid grid-cols-1 gap-8 md:grid-cols-2"
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            <div className="space-y-4">
              <p className="text-xs font-medium uppercase tracking-widest text-primary">
                Continuous SOC 2 operations
              </p>
              <h2
                id="feature-grid-heading"
                className="text-3xl font-medium leading-tight tracking-tight text-foreground md:text-4xl"
              >
                From infrastructure state to audit-ready evidence
              </h2>
            </div>

            <p className="self-end text-base leading-relaxed text-muted-foreground">
              Monitor the systems behind your controls continuously, preserve
              evidence at the source, and keep exceptions visible long before
              an auditor asks for them.
            </p>
          </motion.div>

          <motion.div
            className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3"
            variants={staggeredGrid}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            {features.map(({ icon: Icon, title, body }) => (
              <motion.article
                key={title}
                variants={fadeUp}
                className="h-full rounded-lg border border-border bg-card p-6 shadow-sm"
              >
                <div className="space-y-4">
                  <Icon
                    size={24}
                    strokeWidth={1.75}
                    className="text-primary"
                    aria-hidden="true"
                  />
                  <h3 className="text-xl font-medium leading-snug text-foreground">
                    {title}
                  </h3>
                  <p className="text-base leading-relaxed text-muted-foreground">
                    {body}
                  </p>
                </div>
              </motion.article>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
