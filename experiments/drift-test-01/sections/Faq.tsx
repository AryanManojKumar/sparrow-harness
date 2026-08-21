"use client"

import { motion } from "motion/react"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

type FaqItem = {
  id: string
  question: string
  answer: string
}

const eyebrow = "Before you book"
const heading = "Questions we get from people who have done this once already"

const items: FaqItem[] = [
  {
    id: "access",
    question: "What access does Ledgerline need to our cloud accounts?",
    answer:
      "A read-only role in each account, created by a Terraform module we publish and you review before applying. No agents on your hosts, no write permissions, no access to customer data paths. Scope can be narrowed per account, and revoking the role stops collection immediately.",
  },
  {
    id: "already-certified",
    question: "We already passed a SOC 2 Type II. What does continuous monitoring add?",
    answer:
      "Type II is judged over an observation window, not on the day you export screenshots. Continuous monitoring means evidence for that window is collected as it happens, so a control that lapsed in month three is caught in month three rather than during fieldwork. The next audit becomes a review of a record that already exists.",
  },
  {
    id: "auditor",
    question: "Does this replace our auditor?",
    answer:
      "No. We do not issue opinions and we are not a CPA firm. Ledgerline produces the evidence your auditor asks for, in the form they ask for it, and gives them a scoped read-only view so requests stop routing through your engineers. Firms you are already working with can keep the engagement.",
  },
  {
    id: "drift",
    question: "What happens when a control drifts out of compliance?",
    answer:
      "You get a single alert naming the failing resource, the control it maps to, the owner on record, and the specific change that broke it. The timeline is retained: when it broke, when it was fixed, and who fixed it. That interval is what an auditor asks about, so it is documented rather than reconstructed later.",
  },
  {
    id: "timeline",
    question: "How long before we see real evidence?",
    answer:
      "First collection completes within about an hour of the role being applied. Most teams reach full control coverage in the first week, with the remainder being policy and personnel items that need a human decision rather than an integration.",
  },
  {
    id: "frameworks",
    question: "Do you cover frameworks beyond SOC 2?",
    answer:
      "SOC 2 is what we are built around, and it is where the control mappings are deepest. ISO 27001 and HIPAA share a large share of those controls, so both are supported against the same evidence stream. We would rather say that plainly than claim a framework grid we cannot stand behind.",
  },
]

export default function Faq() {
  return (
    <section id="faq" className="bg-muted py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6">
        <div className="mx-auto max-w-2xl">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="space-y-4"
          >
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              {eyebrow}
            </p>
            <h2 className="text-3xl leading-tight tracking-tight text-foreground md:text-4xl">
              {heading}
            </h2>
          </motion.div>

          <div className="mt-8 border-t border-border">
            <Accordion type="single" collapsible defaultValue={items[0].id}>
              {items.map((item, index) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{
                    duration: 0.4,
                    ease: "easeOut",
                    delay: 0.06 * (index + 1),
                  }}
                >
                  <AccordionItem
                    value={item.id}
                    className="border-b border-border last:border-b"
                  >
                    <AccordionTrigger className="items-center gap-8 py-5 text-base font-medium leading-snug text-foreground no-underline transition-colors duration-150 hover:text-primary hover:no-underline">
                      {item.question}
                    </AccordionTrigger>
                    <AccordionContent className="pb-5 pr-8 text-base leading-relaxed text-muted-foreground">
                      <p>{item.answer}</p>
                    </AccordionContent>
                  </AccordionItem>
                </motion.div>
              ))}
            </Accordion>
          </div>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{
              duration: 0.4,
              ease: "easeOut",
              delay: 0.06 * (items.length + 1),
            }}
            className="mt-8 text-sm leading-normal text-muted-foreground"
          >
            Still deciding?{" "}
            <a
              href="/docs"
              className="text-primary underline underline-offset-4 transition-colors duration-150 hover:text-foreground"
            >
              Read the docs
            </a>{" "}
            for the full control mapping, or{" "}
            <a
              href="/demo"
              className="text-primary underline underline-offset-4 transition-colors duration-150 hover:text-foreground"
            >
              book a demo
            </a>{" "}
            and bring your last audit&rsquo;s request list.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
