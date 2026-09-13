"use client";

import { useState } from "react";
import {
  Check,
  FileDiff,
  Fingerprint,
  GitBranch,
  ListTree,
  type LucideIcon,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

type Feature = {
  label: string;
  title: string;
  body: string;
  mechanism: string[];
  icon: LucideIcon;
};

const features: Feature[] = [
  {
    label: "shared-plan.yaml",
    title: "Shared execution plan",
    body: "Work is recorded as versioned plan entries with explicit repository scope, ownership, dependencies, and acceptance checks. Every assigned run points back to the entry it is expected to satisfy.",
    mechanism: [
      "Scopes changed paths before an agent starts",
      "Records dependencies between concurrent tasks",
      "Keeps acceptance checks beside the requested change",
    ],
    icon: ListTree,
  },
  {
    label: "orchestrator.plugin",
    title: "Repository and agent orchestration",
    body: "Repository plugins prepare isolated worktrees and enforce path boundaries. Agent plugins receive the same scoped task contract, so different models can run without changing the review surface.",
    mechanism: [
      "Pins each worktree to a known base commit",
      "Applies concurrency locks to overlapping paths",
      "Normalizes agent output into one run contract",
    ],
    icon: GitBranch,
  },
  {
    label: "run.trace",
    title: "Explicit change provenance",
    body: "A run trace binds the plan entry, agent adapter, base commit, executed commands, outputs, and changed files to one run ID. Traceability is stored as an artifact, not inferred from the final patch.",
    mechanism: [
      "Links commands and outputs to the producing run",
      "Retains the base commit used for generation",
      "Attributes every changed path to its plan entry",
    ],
    icon: Fingerprint,
  },
  {
    label: "patchset.diff",
    title: "Reviewable diffs before landing",
    body: "Proposed changes are assembled as file-level diffs against the pinned base. Review comments and required decisions remain attached to their hunks, and the landing adapter stays gated until approval.",
    mechanism: [
      "Presents additions and removals by file and hunk",
      "Keeps unresolved comments attached to patch context",
      "Requires an approval state before the landing adapter runs",
    ],
    icon: FileDiff,
  },
];

function FeatureUnit({
  feature,
  index,
}: {
  feature: Feature;
  index: number;
}) {
  const [inspecting, setInspecting] = useState(false);
  const reduceMotion = useReducedMotion();
  const Icon = feature.icon;
  const panelId = `feature-mechanism-${index}`;

  return (
    <motion.article
      initial={{ opacity: 0, x: reduceMotion ? 0 : 8 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      whileHover={{
        boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
        transition: { duration: 0.14, ease: "easeOut" },
      }}
      className="grid h-full grid-cols-[auto_1fr] overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]"
    >
      <div className="relative w-5 border-r border-border bg-muted" aria-hidden="true">
        <motion.span
          animate={{
            y: reduceMotion ? 0 : inspecting ? 48 : 0,
            opacity: inspecting ? 1 : 0.8,
            backgroundColor: inspecting
              ? "oklch(0.455 0.128 239)"
              : "oklch(0.755 0.145 78)",
          }}
          transition={{
            duration: reduceMotion ? 0 : 0.24,
            ease: "easeOut",
          }}
          className="absolute right-0 top-5 size-2 translate-x-1/2 rounded-full border border-card"
        />
      </div>

      <div className="space-y-8 p-5 md:p-8">
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-primary">
            <Icon aria-hidden="true" className="size-5" strokeWidth={1.75} />
            <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em]">
              {feature.label}
            </span>
          </div>

          <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
            {feature.title}
          </h3>

          <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
            {feature.body}
          </p>
        </div>

        <div className="space-y-3">
          <button
            type="button"
            aria-expanded={inspecting}
            aria-controls={panelId}
            onClick={() => setInspecting((current) => !current)}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-5 py-3 font-body text-sm font-normal leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {inspecting ? (
              <Check aria-hidden="true" className="size-5 text-primary" />
            ) : (
              <span
                aria-hidden="true"
                className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-accent"
              >
                !
              </span>
            )}
            {inspecting ? "Hide mechanism" : "Inspect mechanism"}
          </button>

          <AnimatePresence initial={false}>
            {inspecting ? (
              <motion.div
                id={panelId}
                initial={{ opacity: 0, x: reduceMotion ? 0 : 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: reduceMotion ? 0 : 8 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.18,
                  ease: "easeOut",
                }}
                className="rounded-md border border-border bg-muted p-5"
              >
                <ul className="space-y-3">
                  {feature.mechanism.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-2 font-body text-sm font-normal leading-6 text-foreground"
                    >
                      <span
                        aria-hidden="true"
                        className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary"
                      >
                        +
                      </span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </motion.article>
  );
}

export default function FeatureGrid() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="bg-muted py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="space-y-8 md:space-y-10">
          <motion.header
            initial={{ opacity: 0, x: reduceMotion ? 0 : 8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="max-w-3xl space-y-3"
          >
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              Harness architecture
            </p>
            <h2 className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl">
              A plugin harness with provenance at every boundary.
            </h2>
            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              Planning, repository access, agent execution, trace capture, and
              landing policy are independent plugins. Their shared artifact
              contract makes every run traceable from requested scope to the
              diff presented for review.
            </p>
          </motion.header>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 md:gap-8">
            {features.map((feature, index) => (
              <FeatureUnit
                key={feature.label}
                feature={feature}
                index={index}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
