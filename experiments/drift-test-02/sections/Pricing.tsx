"use client";

import { Check } from "lucide-react";
import { motion } from "motion/react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const tiers = [
  {
    name: "Foundation",
    price: "$600",
    cadence: "per month",
    summary:
      "For teams establishing continuous controls before their first or next SOC 2 audit.",
    features: [
      "One cloud environment",
      "Continuous control monitoring",
      "Automated evidence collection",
      "SOC 2 policy templates",
      "Auditor evidence exports",
    ],
    cta: "Book a demo",
  },
  {
    name: "Scale",
    price: "$1,500",
    cadence: "per month",
    summary:
      "For growing fintech teams managing an active audit and a changing infrastructure footprint.",
    features: [
      "Multiple cloud environments",
      "Custom controls and evidence rules",
      "Automated access reviews",
      "Continuous vendor monitoring",
      "Dedicated compliance support",
    ],
    cta: "Book a demo",
    recommended: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "annual agreement",
    summary:
      "For organizations with multiple entities, frameworks, or specialized security requirements.",
    features: [
      "Unlimited cloud environments",
      "Multiple entities and workspaces",
      "Custom framework mapping",
      "SAML SSO and SCIM provisioning",
      "Security review and onboarding plan",
    ],
    cta: "Contact sales",
  },
];

function entrance(delay: number) {
  return {
    initial: { opacity: 0, y: 12 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.2 },
    transition: {
      duration: 0.4,
      delay,
      ease: "easeOut" as const,
    },
  };
}

export default function Pricing() {
  return (
    <section className="bg-background py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div {...entrance(0)} className="space-y-4">
          <p className="text-xs font-medium uppercase tracking-widest text-primary">
            Pricing
          </p>
          <h2 className="text-3xl font-medium leading-tight tracking-tight text-foreground md:text-4xl">
            Continuous SOC 2 compliance, priced for the work involved.
          </h2>
          <p className="text-base leading-relaxed text-muted-foreground">
            Every plan includes continuous monitoring and audit-ready evidence.
            Choose based on infrastructure complexity and the level of support
            your team needs.
          </p>
        </motion.div>

        <div className="mt-8 grid items-stretch gap-8 md:grid-cols-3">
          {tiers.map((tier, index) => (
            <motion.div
              key={tier.name}
              {...entrance((index + 1) * 0.06)}
              className="h-full"
            >
              <Card className="flex h-full flex-col rounded-lg shadow-sm">
                <CardHeader className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-xl leading-snug">
                      {tier.name}
                    </CardTitle>
                    {tier.recommended ? (
                      <Badge className="rounded-lg bg-accent text-foreground">
                        Recommended
                      </Badge>
                    ) : null}
                  </div>

                  <div className="flex items-baseline gap-3">
                    <p className="text-3xl font-medium leading-tight text-foreground md:text-4xl">
                      {tier.price}
                    </p>
                    <p className="text-sm leading-normal text-muted-foreground">
                      {tier.cadence}
                    </p>
                  </div>

                  <p className="text-base leading-relaxed text-muted-foreground">
                    {tier.summary}
                  </p>
                </CardHeader>

                <CardContent className="flex-1">
                  <ul className="space-y-4">
                    {tier.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-3 text-sm leading-normal text-foreground"
                      >
                        <Check
                          className="size-4 shrink-0 text-primary"
                          aria-hidden="true"
                        />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter className="mt-auto">
                  <Button
                    asChild
                    className="w-full rounded-lg transition-colors duration-150"
                  >
                    <a href="#book-demo">{tier.cta}</a>
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
