"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

type ActionPath = "try" | "source";

const pathDetails: Record<
  ActionPath,
  {
    label: string;
    file: string;
    command: string;
    state: string;
  }
> = {
  try: {
    label: "TRY PATH",
    file: "workspace/connect.sh",
    command: "npx agent-harness@latest start --repo .",
    state: "+ repository connection requested",
  },
  source: {
    label: "SOURCE PATH",
    file: "checkout/install.sh",
    command:
      "git clone https://github.com/agent-harness/harness.git && cd harness && pnpm install",
    state: "+ local checkout ready for configuration",
  },
};

export default function Cta() {
  const [activePath, setActivePath] = useState<ActionPath>("try");
  const reduceMotion = useReducedMotion();
  const detail = pathDetails[activePath];

  const selectPath = (path: ActionPath) => {
    setActivePath(path);
  };

  return (
    <section className="bg-muted py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <motion.div
          className="relative overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]"
          whileHover={{
            boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
          }}
          transition={{ duration: 0.14, ease: "easeOut" }}
        >
          <div className="grid gap-5 p-5 md:grid-cols-2 md:gap-8 md:p-8">
            <div className="space-y-8 md:space-y-10">
              <div className="space-y-3">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                  READY FOR REVIEW
                </p>
                <h2 className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl">
                  Try a reviewable run now, or install the harness from source.
                </h2>
                <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                  Connect a repository to generate a shared plan, assigned run
                  trace, and file-level diff. Nothing lands until an engineer
                  approves the proposed change.
                </p>
              </div>

              <div className="space-y-3">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  PREREQUISITE
                </p>
                <p className="font-body text-sm font-normal leading-6 text-foreground">
                  Node.js 20+, pnpm 9+, Git 2.40+, and a repository you can
                  create a branch in.
                </p>
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <motion.a
                  href="/start"
                  aria-pressed={activePath === "try"}
                  onFocus={() => selectPath("try")}
                  onPointerEnter={() => selectPath("try")}
                  onPointerDown={() => selectPath("try")}
                  className="flex items-center justify-between gap-2 rounded-md border border-foreground bg-accent px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] focus-visible:border-primary focus-visible:outline-none"
                  whileHover={{
                    boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
                  }}
                  transition={{ duration: 0.14, ease: "easeOut" }}
                >
                  <span>Start free — connect a repo</span>
                  <span aria-hidden="true">
                    {activePath === "try" ? "✓" : "→"}
                  </span>
                </motion.a>

                <motion.a
                  id="source-install"
                  href="#install-command"
                  aria-pressed={activePath === "source"}
                  onFocus={() => selectPath("source")}
                  onPointerEnter={() => selectPath("source")}
                  onPointerDown={() => selectPath("source")}
                  className="flex items-center justify-between gap-2 rounded-md border border-primary bg-card px-5 py-3 font-body text-sm font-medium leading-6 text-primary shadow-[0_2px_0_0_oklch(0.805_0.032_235)] focus-visible:border-foreground focus-visible:outline-none"
                  whileHover={{
                    boxShadow: "0 4px 0 0 oklch(0.805 0.032 235)",
                  }}
                  transition={{ duration: 0.14, ease: "easeOut" }}
                >
                  <span>Install source — clone locally</span>
                  <span aria-hidden="true">
                    {activePath === "source" ? "✓" : "→"}
                  </span>
                </motion.a>
              </div>

              <a
                href="/docs/quick-start"
                className="inline-flex items-center gap-2 font-body text-sm font-medium leading-6 text-primary focus-visible:outline-none focus-visible:underline"
              >
                Read the Quick start
                <span aria-hidden="true">→</span>
              </a>
            </div>

            <div
              id="install-command"
              className="flex min-w-0 overflow-hidden rounded-md border border-border bg-card"
            >
              <aside
                aria-label="Review gutter"
                className="relative w-8 border-r border-primary bg-muted"
              >
                <motion.span
                  aria-hidden="true"
                  className="absolute left-0 right-0 mx-auto flex h-5 w-5 items-center justify-center bg-accent font-mono text-xs font-medium leading-5 text-foreground"
                  animate={{
                    top: activePath === "try" ? "22%" : "68%",
                  }}
                  transition={
                    reduceMotion
                      ? { duration: 0 }
                      : { duration: 0.24, ease: "easeOut" }
                  }
                >
                  !
                </motion.span>
              </aside>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2 border-b border-border bg-muted p-5">
                  <div className="space-y-3">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                      {detail.label}
                    </p>
                    <p className="break-all font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                      {detail.file}
                    </p>
                  </div>
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    @@ SETUP
                  </span>
                </div>

                <div className="border-l border-primary">
                  <AnimatePresence mode="wait" initial={false}>
                    <motion.div
                      key={activePath}
                      aria-live="polite"
                      initial={{
                        opacity: 0,
                        x: reduceMotion ? 0 : 8,
                      }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{
                        opacity: 0,
                        x: reduceMotion ? 0 : -8,
                      }}
                      transition={{ duration: 0.18, ease: "easeOut" }}
                    >
                      <div className="grid grid-cols-[auto_1fr] border-b border-border bg-card">
                        <span className="border-r border-border p-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                          01
                        </span>
                        <code className="break-all p-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-foreground">
                          <span className="text-primary">+ </span>
                          {detail.command}
                        </code>
                      </div>

                      <div className="grid grid-cols-[auto_1fr] bg-muted">
                        <span className="border-r border-border p-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                          02
                        </span>
                        <p className="p-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                          {detail.state}
                        </p>
                      </div>
                    </motion.div>
                  </AnimatePresence>
                </div>

                <div className="border-t border-border p-5">
                  <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
                    The first run opens as a proposed diff with its plan entry,
                    run ID, file path, and approval checkpoint attached.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
