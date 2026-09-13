"use client";

import { motion, useReducedMotion } from "motion/react";

const restingShadow = "0 2px 0 0 oklch(0.805 0.032 235)";
const hoverShadow = "0 4px 0 0 oklch(0.805 0.032 235)";

export default function Testimonial() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <section
      aria-label="Customer adoption evidence"
      className="bg-background py-20 md:py-28 lg:py-32"
    >
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-5 sm:px-8 md:grid-cols-12 md:gap-8">
        <motion.figure
          initial={{
            opacity: 0,
            x: prefersReducedMotion ? 0 : 8,
            boxShadow: restingShadow,
          }}
          whileInView={{
            opacity: 1,
            x: 0,
            boxShadow: restingShadow,
          }}
          whileHover={{ boxShadow: hoverShadow }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{
            opacity: { duration: 0.18, ease: "easeOut" },
            x: { duration: prefersReducedMotion ? 0 : 0.18, ease: "easeOut" },
            boxShadow: { duration: 0.14, ease: "easeOut" },
          }}
          className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] md:col-span-10 md:col-start-2"
        >
          <div className="flex items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3 sm:px-8">
            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
              evidence/adoption-review.md
            </span>
            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
              customer evidence
            </span>
          </div>

          <div className="grid grid-cols-[auto_1fr] gap-5 px-5 py-8 sm:px-8 md:gap-8">
            <div
              aria-hidden="true"
              className="flex border-r border-border pr-5 text-right sm:pr-8"
            >
              <div className="space-y-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                <div>118</div>
                <div className="text-primary">119&nbsp;+</div>
                <div>120</div>
                <div className="border-y-2 border-l-2 border-primary text-accent">
                  &nbsp;!
                </div>
                <div>121</div>
              </div>
            </div>

            <div className="space-y-8 md:space-y-10">
              <blockquote className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                “Agent adoption was stuck in single digits because reviewers
                could not reconstruct what each run had changed or why. Once
                every run started from a shared plan and returned a file-level
                diff with an approval checkpoint, adoption moved to over 80%
                within two quarters.”
              </blockquote>

              <figcaption className="space-y-3 border-t border-border pt-5">
                <div className="font-body text-sm font-medium leading-6 text-foreground">
                  Elena Marquez
                </div>
                <div className="font-body text-sm font-normal leading-6 text-muted-foreground">
                  VP Engineering, Northline Logistics
                </div>
                <div className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  74 engineers · 18 repositories · TypeScript, Go, Terraform
                </div>
              </figcaption>
            </div>
          </div>
        </motion.figure>
      </div>
    </section>
  );
}
