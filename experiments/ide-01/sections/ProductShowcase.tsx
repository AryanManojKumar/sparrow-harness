"use client";

import Image from "next/image";
import { ArrowRight, Check, GitBranch, MessageSquare } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

const captures = [
  {
    id: "parallel-runs",
    label: "PARALLEL RUNS",
    path: "repo://platform/workspaces",
    title: "Bounded work runs in isolated workspaces.",
    description:
      "Each agent receives a shared-plan entry, repository scope, and its own workspace so concurrent changes remain attributable.",
    image: "/assets/product-showcase-1.png",
    alt: "Multiple coding agents running concurrently in separate repository workspaces.",
    lines: ["118", "119", "120"],
    status: "run_8f31",
  },
  {
    id: "shared-projects",
    label: "SHARED PROJECT",
    path: "plan://auth-hardening",
    title: "The plan stays attached to every conversation.",
    description:
      "Projects collect task ownership, agent context, and run state around the same repository plan instead of scattering them across chats.",
    image: "/assets/product-showcase-2.png",
    alt: "Projects organizing active coding-agent conversations under a shared plan.",
    lines: ["204", "205", "206"],
    status: "plan_42c",
  },
  {
    id: "command-view",
    label: "COMMAND VIEW",
    path: "runs://active",
    title: "Coordination is visible from one command view.",
    description:
      "Run status, workspace progress, and blocked assignments are surfaced together so an engineer can redirect work with the repository state in view.",
    image: "/assets/product-showcase-3.png",
    alt: "Central command view coordinating coding-agent status and workspace progress.",
    lines: ["311", "312", "313"],
    status: "fleet_17a",
  },
  {
    id: "diff-review",
    label: "DIFF REVIEW",
    path: "src/auth/session.ts",
    title: "Completed work returns as a file-level diff.",
    description:
      "Changed lines, run ownership, and unresolved comments remain inspectable before an approval allows the patch to land.",
    image: "/assets/product-showcase-4.png",
    alt: "Completed coding-agent change opened as a reviewable file-level diff.",
    lines: ["468", "469", "470"],
    status: "patch_a91",
  },
];

export default function ProductShowcase() {
  const [activeCapture, setActiveCapture] = useState(captures[0].id);
  const reduceMotion = useReducedMotion();

  return (
    <section
      className="bg-background py-20 md:py-28 lg:py-32"
      aria-labelledby="product-showcase-heading"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid gap-5 md:grid-cols-2 md:gap-8">
          <div className="space-y-3">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              Repository command center
            </p>
            <h2
              id="product-showcase-heading"
              className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl"
            >
              Coordinate the fleet. Review the patch.
            </h2>
          </div>

          <div className="space-y-8 md:space-y-10">
            <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
              A shared plan assigns bounded work to isolated repository
              workspaces. The command view keeps ownership and run state
              together, then returns completed work as file-level diffs with
              explicit approval checkpoints before merge.
            </p>

            <motion.a
              href="/signup"
              className="inline-flex items-center gap-2 rounded-md border border-foreground bg-accent px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              whileHover={{
                boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
              }}
              transition={{ duration: 0.14, ease: "easeOut" }}
            >
              Start free
              <ArrowRight aria-hidden="true" />
            </motion.a>
          </div>
        </div>

        <div className="grid gap-5 pt-20 md:grid-cols-2 md:gap-8 md:pt-28 lg:pt-32">
          {captures.map((capture) => {
            const isActive = activeCapture === capture.id;

            return (
              <motion.article
                key={capture.id}
                initial={{
                  opacity: 0,
                  x: reduceMotion ? 0 : -8,
                }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
              >
                <motion.button
                  type="button"
                  aria-pressed={isActive}
                  aria-label={`Inspect ${capture.title}`}
                  onClick={() => setActiveCapture(capture.id)}
                  onFocus={() => setActiveCapture(capture.id)}
                  className={`block w-full overflow-hidden rounded-md border bg-card text-left shadow-[0_2px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                    isActive ? "border-primary" : "border-border"
                  }`}
                  whileHover={{
                    boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
                  }}
                  transition={{ duration: 0.14, ease: "easeOut" }}
                >
                  <div className="flex items-center justify-between gap-2 border-b border-border bg-muted p-5">
                    <div className="flex min-w-0 items-center gap-2">
                      <GitBranch
                        className="shrink-0 text-primary"
                        aria-hidden="true"
                      />
                      <span className="truncate font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                        {capture.path}
                      </span>
                    </div>

                    <span
                      className={`flex shrink-0 items-center gap-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] ${
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground"
                      }`}
                    >
                      {isActive && <Check aria-hidden="true" />}
                      {capture.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-[auto_1fr]">
                    <div className="flex flex-col justify-between border-r border-border bg-muted p-5">
                      <div className="space-y-3">
                        {capture.lines.map((line) => (
                          <span
                            key={line}
                            className="block font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground"
                          >
                            {line}
                          </span>
                        ))}
                      </div>

                      <AnimatePresence>
                        {isActive && (
                          <motion.span
                            initial={{
                              opacity: 0,
                              x: reduceMotion ? 0 : -8,
                            }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{
                              opacity: 0,
                              x: reduceMotion ? 0 : -8,
                            }}
                            transition={{
                              duration: 0.24,
                              ease: "easeOut",
                            }}
                            className="flex items-center gap-2 rounded-sm border border-foreground bg-accent p-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground"
                            aria-label="Review checkpoint selected"
                          >
                            <MessageSquare aria-hidden="true" />
                            !
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </div>

                    <div className="min-w-0 overflow-hidden bg-card">
                      <motion.div
                        animate={{
                          opacity: isActive ? 1 : 0.96,
                          x: reduceMotion ? 0 : isActive ? 0 : -8,
                        }}
                        transition={{ duration: 0.18, ease: "easeOut" }}
                      >
                        <Image
                          src={capture.image}
                          alt={capture.alt}
                          width={1536}
                          height={1024}
                          sizes="(min-width: 768px) 50vw, 100vw"
                          className="h-auto w-full"
                          priority={capture.id === "parallel-runs"}
                        />
                      </motion.div>
                    </div>
                  </div>

                  <div className="space-y-3 border-t border-border p-5">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      {capture.label}
                    </p>
                    <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
                      {capture.title}
                    </h3>
                    <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                      {capture.description}
                    </p>
                  </div>
                </motion.button>
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
