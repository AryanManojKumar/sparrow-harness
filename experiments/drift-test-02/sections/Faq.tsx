"use client";

import { motion } from "motion/react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqItems = [
  {
    question: "How much access do you need to our infrastructure?",
    answer:
      "Connections use read-only access wherever the provider supports it. We collect configuration and control evidence from your cloud, identity, code, and device systems without changing resources or deployment settings.",
  },
  {
    question: "Does this replace our SOC 2 auditor?",
    answer:
      "No. An independent CPA firm must still issue the SOC 2 report. The platform keeps controls monitored and evidence organized throughout the audit period, so your auditor receives a clear, traceable evidence set instead of a last-minute export.",
  },
  {
    question: "Can we use our existing controls and policies?",
    answer:
      "Yes. You can map existing controls to the platform rather than adopting a generic program. Policies, owners, review schedules, and evidence requirements remain visible, with changes recorded for the audit trail.",
  },
  {
    question: "What happens when a control fails?",
    answer:
      "The relevant owner receives a finding with the affected system, observed configuration, and expected control state. The platform preserves the detection and remediation history so exceptions can be explained during the audit.",
  },
  {
    question: "How long does implementation take?",
    answer:
      "Most teams connect their core systems and establish an initial control baseline within a few days. Timing depends on the number of integrations, the maturity of your existing program, and whether you are preparing for Type I or collecting evidence for Type II.",
  },
  {
    question: "Will this work with our existing compliance stack?",
    answer:
      "The platform is designed to connect with the systems technical teams already use, including cloud providers, identity platforms, source control, ticketing, HR systems, and endpoint management. The demo can confirm coverage for your specific stack.",
  },
];

const entrance = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
};

export default function Faq() {
  return (
    <section
      aria-labelledby="faq-heading"
      className="bg-muted py-24 md:py-32"
    >
      <div className="mx-auto max-w-6xl px-6">
        <div className="mx-auto max-w-3xl space-y-8">
          <motion.div
            className="space-y-4"
            initial={entrance.initial}
            whileInView={entrance.animate}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <p className="text-xs font-medium uppercase tracking-widest text-primary">
              Frequently asked questions
            </p>
            <h2
              id="faq-heading"
              className="text-3xl font-medium leading-tight tracking-tight text-foreground md:text-4xl"
            >
              What to know before connecting your systems
            </h2>
          </motion.div>

          <motion.div
            initial={entrance.initial}
            whileInView={entrance.animate}
            viewport={{ once: true, amount: 0.15 }}
            transition={{ duration: 0.4, delay: 0.06, ease: "easeOut" }}
          >
            <Accordion
              type="single"
              collapsible
              defaultValue="access"
              className="w-full"
            >
              {faqItems.map((item, index) => (
                <AccordionItem
                  key={item.question}
                  value={index === 0 ? "access" : `item-${index + 1}`}
                  className="border-border"
                >
                  <AccordionTrigger className="text-left text-base font-medium leading-relaxed text-foreground transition-colors duration-150 hover:text-primary hover:no-underline">
                    {item.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-base leading-relaxed text-muted-foreground">
                    {item.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
