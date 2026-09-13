import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqItems = [
  {
    value: "auditor",
    question: "Does this replace our SOC 2 auditor?",
    answer:
      "No. Your auditor remains responsible for the independent examination and opinion. The platform maintains your control environment, collects supporting evidence, and organizes it with source, collector, timestamp, and control provenance so the audit starts with a reviewable record rather than a manual evidence request.",
  },
  {
    value: "setup",
    question: "How much work is required to get connected?",
    answer:
      "Most teams begin with read-only connections to their cloud, identity, source control, ticketing, and security systems. Existing controls are mapped before collection begins, so you can review scope and ownership without rebuilding your compliance program around a generic template.",
  },
  {
    value: "controls",
    question: "Can we keep our existing controls and risk framework?",
    answer:
      "Yes. Controls can be imported and mapped to SOC 2 criteria while preserving your current language, owners, test procedures, and internal references. Standard mappings are available where useful, but they do not replace the controls your company actually operates.",
  },
  {
    value: "evidence",
    question: "What makes the collected evidence audit-ready?",
    answer:
      "Each artifact retains its source system, SOC 2 control mapping, collection time, verification state, and collection method. Evidence is stored as a traceable record rather than an unexplained screenshot, giving reviewers a clear chain from the control requirement to the underlying system state.",
  },
  {
    value: "exceptions",
    question: "Will continuous monitoring create a stream of noisy alerts?",
    answer:
      "Monitoring is evaluated against the control's defined cadence and scope. Exceptions are grouped by control and routed to the responsible owner with the failed test and supporting context. A transient system event is not treated the same as a sustained control failure.",
  },
  {
    value: "access",
    question: "What access does the platform need?",
    answer:
      "Integrations use the minimum read permissions required for evidence collection wherever the source supports them. Credentials and collection activity are logged, and access can be reviewed or revoked through the connected system. Write access is not required to monitor infrastructure controls.",
  },
];

export default function Faq() {
  return (
    <section
      className="bg-muted py-20 md:py-28"
      aria-labelledby="faq-heading"
    >
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="mx-auto w-full space-y-8 md:w-2/3 md:space-y-10">
          <div className="space-y-3">
            <p className="font-mono text-xs font-medium uppercase leading-4 tracking-[0.08em] text-muted-foreground">
              SOC 2 / Audit readiness
            </p>
            <h2
              id="faq-heading"
              className="font-display text-4xl font-semibold leading-none tracking-[-0.02em] text-foreground md:text-5xl"
            >
              Questions before you connect your systems
            </h2>
          </div>

          <Accordion
            type="single"
            defaultValue="auditor"
            collapsible
            className="border-y border-border"
          >
            {faqItems.map((item) => (
              <AccordionItem
                key={item.value}
                value={item.value}
                className="border-border last:border-b-0"
              >
                <AccordionTrigger className="py-6 text-left font-display text-2xl font-semibold leading-[1.1] tracking-[-0.01em] text-foreground hover:no-underline focus-visible:ring-accent md:text-3xl">
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="pb-6 font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
}
