"use client";

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

const stages = [
  {
    label: "Shared plan entry",
    symbol: "+",
    symbolClass: "bg-primary text-primary-foreground",
    primary: "auth/session.ts → tighten token validation",
    metadata: "owner: unassigned · base: 8f2c1a7",
    action: "Assign scoped run",
  },
  {
    label: "Assigned run",
    symbol: "→",
    symbolClass: "bg-primary text-primary-foreground",
    primary: "run/cordis-184 · owner: agent-03",
    metadata: "scope: src/auth/session.ts · writes outside scope rejected",
    action: "Reveal review diff",
  },
  {
    label: "Reviewable diff",
    symbol: "!",
    symbolClass: "bg-accent text-foreground",
    primary: "src/auth/session.ts · +18 −6",
    metadata: "@@ -84,9 +84,21 @@ · approval required",
    action: "Diff ready for review",
  },
] as const;

const restingShadow = "0 2px 0 0 oklch(0.805 0.032 235)";
const hoverShadow = "0 4px 0 0 oklch(0.805 0.032 235)";

export default function FeatureDetail() {
  const [stage, setStage] = useState(0);
  const reduceMotion = useReducedMotion();
  const currentStage = stages[stage];
  const isComplete = stage === stages.length - 1;

  return (
    <section className="bg-muted py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-start gap-5 md:gap-8 lg:grid-cols-12">
          <div className="space-y-8 md:space-y-10 lg:col-span-7">
            <div className="space-y-3">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                Model capability / harness control
              </p>
              <h2 className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl">
                The model proposes. The harness governs repository work.
              </h2>
            </div>

            <div className="space-y-3">
              <p className="font-body text-base font-normal leading-7 text-foreground md:text-lg md:leading-8">
                Inside your repository, each agent operates from the same
                versioned plan, commit base, and owned file scope.
              </p>
              <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Model output is treated as a proposal, not an authority. The
                harness binds every run to explicit constraints, records the
                execution path, and returns file-level changes as a diff a
                human can inspect before anything lands.
              </p>
            </div>
          </div>

          <motion.aside
            className="rounded-md border border-border bg-card p-5 shadow-[0_2px_0_0_oklch(0.805_0.032_235)] md:p-8 lg:col-span-5"
            aria-labelledby="cordis-kernel-title"
          >
            <div className="space-y-8">
              <div className="space-y-3">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                  Cordis kernel / control path
                </p>
                <h3
                  id="cordis-kernel-title"
                  className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8"
                >
                  Control lives outside the model.
                </h3>
                <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                  The Cordis kernel resolves a shared-plan entry into a scoped
                  run manifest, checks writes against that scope, records the
                  commit base and tool trace, then emits the resulting patch as
                  a review checkpoint.
                </p>
              </div>

              <div className="grid grid-cols-[auto_1fr] gap-5 rounded-md border border-border bg-muted p-5">
                <div
                  className="relative min-h-20 border-r border-border pr-5"
                  aria-hidden="true"
                >
                  <motion.span
                    className="flex h-5 w-5 items-center justify-center rounded-sm bg-accent font-mono text-xs font-medium leading-5 text-foreground"
                    style={
                      reduceMotion
                        ? { position: "relative", top: stage * 32 }
                        : undefined
                    }
                    animate={{ y: reduceMotion ? 0 : stage * 32 }}
                    transition={{
                      duration: reduceMotion ? 0 : 0.24,
                      ease: "easeOut",
                    }}
                  >
                    !
                  </motion.span>
                </div>

                <div className="min-h-20" aria-live="polite">
                  <AnimatePresence initial={false} mode="wait">
                    <motion.div
                      key={currentStage.label}
                      className="space-y-3"
                      initial={{
                        opacity: 0,
                        x: reduceMotion ? 0 : 8,
                      }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.18, ease: "easeOut" }}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded-sm font-mono text-xs font-medium leading-5 ${currentStage.symbolClass}`}
                          aria-hidden="true"
                        >
                          {currentStage.symbol}
                        </span>
                        <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                          {currentStage.label}
                        </p>
                      </div>
                      <p className="font-mono text-sm font-medium leading-6 text-foreground">
                        {currentStage.primary}
                      </p>
                      <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                        {currentStage.metadata}
                      </p>
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>

              <motion.button
                type="button"
                disabled={isComplete}
                onClick={() =>
                  setStage((current) =>
                    Math.min(current + 1, stages.length - 1),
                  )
                }
                className="w-full rounded-md border border-border bg-card px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:bg-muted disabled:text-muted-foreground"
                style={{ boxShadow: restingShadow }}
                whileHover={
                  isComplete ? { boxShadow: restingShadow } : { boxShadow: hoverShadow }
                }
                transition={{ duration: 0.14, ease: "easeOut" }}
              >
                {currentStage.action}
              </motion.button>
            </div>
          </motion.aside>
        </div>
      </div>
    </section>
  );
}
