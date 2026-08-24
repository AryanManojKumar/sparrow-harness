"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, BookOpen, Check, GitPullRequest } from "lucide-react";
import { useState } from "react";

const stages = [
  {
    label: "PLAN",
    artifact: "shared-plan.yaml",
    summary:
      "Repository work is decomposed into owned entries with file scope and acceptance checks.",
  },
  {
    label: "RUN",
    artifact: "run_0184 · 4 assigned",
    summary:
      "Each agent receives one plan entry, records its run trace, and proposes changes against the same repository state.",
  },
  {
    label: "REVIEW",
    artifact: "3 diffs · approval required",
    summary:
      "Proposed changes arrive as file-level patches with commit context and an explicit approval checkpoint.",
  },
] as const;

const ease = [0.22, 1, 0.36, 1] as const;

export default function Hero() {
  const [activeStage, setActiveStage] = useState(0);
  const reducedMotion = useReducedMotion();
  const active = stages[activeStage];

  return (
    <section className="bg-background py-20 text-foreground md:py-28 lg:py-32">
      <div className="mx-auto grid max-w-7xl px-5 sm:px-8 lg:grid-cols-12 lg:items-center lg:gap-8">
        <motion.div
          className="space-y-8 md:space-y-10 lg:col-span-5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reducedMotion ? 0 : 0.18, ease }}
        >
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
              <span>Branchline</span>
              <span aria-hidden="true" className="text-border">
                /
              </span>
              <span className="text-primary">Developer preview</span>
            </div>

            <h1 className="font-display text-5xl font-semibold leading-[0.94] tracking-[-0.045em] md:text-7xl">
              Coordinate agents. Review the repository diff.
            </h1>

            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Branchline runs a fleet of coding agents against one shared plan.
              Every assignment keeps its file scope, run trace, and proposed
              patch attached, so engineers can inspect the mechanism before any
              change lands.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <motion.a
              href="/signup"
              className="inline-flex items-center gap-2 rounded-md border border-accent bg-accent px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] outline-none focus-visible:ring-2 focus-visible:ring-accent"
              whileHover={{
                boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
              }}
              transition={{ duration: reducedMotion ? 0 : 0.14, ease }}
            >
              Start free
              <ArrowRight aria-hidden="true" className="h-5 w-5" />
            </motion.a>

            <motion.a
              href="/docs"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-5 py-3 font-body text-sm font-medium leading-6 text-primary shadow-[0_2px_0_0_oklch(0.805_0.032_235)] outline-none focus-visible:ring-2 focus-visible:ring-accent"
              whileHover={{
                boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
              }}
              transition={{ duration: reducedMotion ? 0 : 0.14, ease }}
            >
              <BookOpen aria-hidden="true" className="h-5 w-5" />
              Read the docs
            </motion.a>
          </div>
        </motion.div>

        <motion.figure
          id="workflow"
          aria-labelledby="workflow-label"
          className="mt-10 overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)] lg:col-span-7 lg:mt-0"
          initial={{
            opacity: 0,
            x: reducedMotion ? 0 : 8,
          }}
          animate={{ opacity: 1, x: 0 }}
          whileHover={{
            boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
          }}
          transition={{
            duration: reducedMotion ? 0 : 0.18,
            ease,
            boxShadow: {
              duration: reducedMotion ? 0 : 0.14,
              ease,
            },
          }}
        >
          <div className="space-y-3 border-b border-border bg-muted px-5 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <GitPullRequest
                  aria-hidden="true"
                  className="h-5 w-5 text-primary"
                />
                <span
                  id="workflow-label"
                  className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]"
                >
                  Interactive workflow
                </span>
              </div>

              <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                repo://payments/service
              </span>
            </div>

            <div
              className="flex flex-wrap gap-2"
              aria-label="Workflow stage"
            >
              {stages.map((stage, index) => {
                const selected = index === activeStage;

                return (
                  <button
                    key={stage.label}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setActiveStage(index)}
                    className={`rounded-md border px-3 py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-card text-muted-foreground"
                    }`}
                  >
                    0{index + 1} {stage.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex bg-card">
            <div
              aria-label={`Review checkpoint at ${active.label}`}
              className="relative w-8 shrink-0 border-r border-primary bg-muted"
            >
              <div className="flex h-full flex-col items-center justify-around py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                <span>18</span>
                <span>42</span>
                <span>77</span>
              </div>

              <motion.span
                initial={false}
                animate={{
                  top: ["18%", "49%", "79%"][activeStage],
                }}
                transition={{
                  duration: reducedMotion ? 0 : 0.24,
                  ease,
                }}
                className="absolute right-0 flex h-5 w-5 items-center justify-center bg-accent font-mono text-xs font-medium leading-5 text-foreground"
              >
                !
              </motion.span>
            </div>

            <motion.div
              key={activeStage}
              className="min-w-0 flex-1"
              initial={{
                opacity: 0,
                x: reducedMotion ? 0 : 8,
              }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                duration: reducedMotion ? 0 : 0.18,
                ease,
              }}
            >
              <Image
                src="/assets/hero-1.png"
                alt="Branchline repository workspace showing a shared plan dispatched to multiple coding agents and proposed changes presented as reviewable diffs before merge."
                width={1536}
                height={1024}
                priority
                sizes="(min-width: 1024px) 58vw, 100vw"
                className="h-auto w-full"
              />
            </motion.div>
          </div>

          <figcaption className="border-t border-border bg-muted px-5 py-5">
            <motion.div
              key={`caption-${activeStage}`}
              aria-live="polite"
              className="space-y-3"
              initial={{
                opacity: 0,
                x: reducedMotion ? 0 : 8,
              }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                duration: reducedMotion ? 0 : 0.18,
                ease,
              }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                  {active.label}
                </span>
                <span className="flex items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  {activeStage === 2 && (
                    <Check aria-hidden="true" className="h-5 w-5 text-primary" />
                  )}
                  {active.artifact}
                </span>
              </div>

              <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                {active.summary}
              </p>
            </motion.div>
          </figcaption>
        </motion.figure>
      </div>
    </section>
  );
}
