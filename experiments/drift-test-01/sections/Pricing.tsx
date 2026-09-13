"use client";

import { motion } from "motion/react";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";

type Tier = {
  name: string;
  price: string;
  cadence: string;
  summary: string;
  features: string[];
  cta: string;
  recommended?: boolean;
};

const tiers: Tier[] = [
  {
    name: "Starter",
    price: "$499",
    cadence: "per month, billed annually",
    summary:
      "For teams heading into their first SOC 2 Type II with a single cloud account.",
    features: [
      "One cloud account: AWS, GCP, or Azure",
      "SOC 2 Trust Services criteria mapped to controls",
      "Evidence collected on a 24-hour cycle",
      "Policy templates with version history",
      "Control drift alerts in Slack and email",
      "Email support, one business day",
    ],
    cta: "Book a demo",
  },
  {
    name: "Growth",
    price: "$1,400",
    cadence: "per month, billed annually",
    summary:
      "For companies in an active audit cycle, usually with a second framework already in scope.",
    features: [
      "Everything in Starter",
      "Up to five cloud accounts, 200 monitored resources",
      "SOC 2, ISO 27001, and HIPAA control mapping",
      "Auditor workspace with read-only evidence access",
      "Quarterly access reviews and vendor register",
      "Onboarding and offboarding checks from your HRIS",
      "Shared Slack channel, four-hour response",
    ],
    cta: "Book a demo",
    recommended: true,
  },
  {
    name: "Scale",
    price: "Custom",
    cadence: "annual contract",
    summary:
      "For regulated fintechs running multiple entities, auditors, and residency requirements.",
    features: [
      "Everything in Growth",
      "Unlimited accounts, entities, and frameworks",
      "Custom controls and evidence adapters",
      "SSO, SCIM, and exportable audit logs",
      "Data residency in the US or EU",
      "Named compliance engineer, quarterly review",
    ],
    cta: "Talk to sales",
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="bg-muted py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="max-w-2xl space-y-4"
        >
          <p className="text-xs font-medium tracking-widest uppercase text-muted-foreground">
            Pricing
          </p>
          <h2 className="text-3xl leading-tight tracking-tight md:text-4xl">
            Priced by scope, not by seat
          </h2>
          <p className="text-base leading-relaxed text-muted-foreground">
            Every plan runs the same monitoring engine and produces the same
            audit-ready SOC 2 evidence. What changes is how much infrastructure
            it watches, how many frameworks it maps to, and how quickly we pick
            up the phone.
          </p>
        </motion.div>

        <div className="mt-16 grid items-stretch gap-8 md:grid-cols-3">
          {tiers.map((tier, i) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.4, ease: "easeOut", delay: i * 0.06 }}
              className="flex h-full flex-col rounded-lg border border-border bg-background p-8 shadow-sm transition-shadow duration-150 hover:shadow-md"
            >
              <div className="flex min-h-8 items-center justify-between gap-4">
                <h3 className="text-xl leading-snug font-medium">
                  {tier.name}
                </h3>
                {tier.recommended ? (
                  <span className="rounded-md bg-accent px-2 py-1 text-xs font-medium tracking-widest uppercase text-accent-foreground">
                    Recommended
                  </span>
                ) : null}
              </div>

              <div className="mt-8 space-y-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl leading-tight font-medium tracking-tight">
                    {tier.price}
                  </span>
                  <span className="text-sm leading-normal text-muted-foreground">
                    {tier.cadence}
                  </span>
                </div>
                <p className="min-h-16 text-sm leading-normal text-muted-foreground">
                  {tier.summary}
                </p>
              </div>

              <div className="mt-8 border-t border-border pt-8">
                <ul className="space-y-4">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex gap-4">
                      <Check
                        aria-hidden="true"
                        className="mt-1 size-4 shrink-0 text-primary"
                      />
                      <span className="text-sm leading-normal">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-8 flex flex-1 flex-col justify-end">
                <Button size="lg" className="w-full">
                  {tier.cta}
                </Button>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.4, ease: "easeOut", delay: 0.18 }}
          className="mt-16 text-sm leading-normal text-muted-foreground"
        >
          Prices in USD. Auditor accounts, evidence export, and the full control
          library are included on every plan.{" "}
          <a
            href="/docs"
            className="text-foreground underline underline-offset-4 transition-colors duration-150 hover:text-primary"
          >
            Read the docs
          </a>{" "}
          for the control catalogue and integration list.
        </motion.p>
      </div>
    </section>
  );
}
