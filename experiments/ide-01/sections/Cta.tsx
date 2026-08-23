"use client";

import { useState } from "react";
import { ArrowRight, Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";

const launchCommand = "npx agent-harness init --repo .";

export default function Cta() {
  const [copied, setCopied] = useState(false);

  async function copyCommand() {
    if (!navigator.clipboard) return;

    await navigator.clipboard.writeText(launchCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section id="start" className="bg-muted py-20 md:py-28 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid gap-5 md:grid-cols-2 md:gap-8">
          <div className="space-y-8 md:space-y-10">
            <div className="space-y-3 border-l-2 border-primary pl-5">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
                Start a reviewable run
              </p>
              <h2 className="font-display text-3xl font-semibold leading-[1.02] tracking-[-0.035em] text-foreground md:text-5xl">
                Put the harness on a repository you already know.
              </h2>
              <p className="max-w-2xl font-body text-base font-normal leading-7 text-muted-foreground md:text-lg md:leading-8">
                Create a local workspace, define the shared plan, and inspect every
                agent change as a file-level diff before anything lands.
              </p>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                asChild
                className="rounded-md bg-accent font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:bg-accent hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)]"
              >
                <a href="/start">
                  Start free
                  <ArrowRight aria-hidden="true" />
                </a>
              </Button>

              <Button
                asChild
                variant="outline"
                className="rounded-md border-border bg-card font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:bg-card hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)]"
              >
                <a href="/docs/install-from-source">Install from source</a>
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                Quick Start
              </p>
              <a
                href="/docs/quick-start"
                className="inline-flex items-center gap-2 font-body text-sm font-normal leading-6 text-primary"
              >
                Read the docs
                <ArrowRight aria-hidden="true" className="size-4" />
              </a>
            </div>

            <div className="overflow-hidden rounded-md border border-border bg-card shadow-[0_2px_0_0_oklch(0.805_0.032_235)]">
              <div className="flex items-center justify-between gap-2 border-b border-border bg-muted px-5 py-3">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 rounded-full bg-accent"
                  />
                  <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                    local / checkout
                  </span>
                </div>
                <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-muted-foreground">
                  shell
                </span>
              </div>

              <div className="grid grid-cols-[auto_1fr_auto] items-center gap-5 px-5 py-5">
                <span
                  aria-hidden="true"
                  className="font-mono text-sm font-normal leading-6 text-muted-foreground"
                >
                  01
                </span>
                <code className="overflow-x-auto font-mono text-sm font-normal leading-6 text-foreground">
                  <span className="text-primary">$</span> {launchCommand}
                </code>
                <button
                  type="button"
                  onClick={copyCommand}
                  className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-5 py-3 font-body text-sm font-medium leading-6 text-foreground shadow-[0_2px_0_0_oklch(0.805_0.032_235)] transition-shadow duration-[140ms] hover:shadow-[0_4px_0_0_oklch(0.805_0.032_235)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label={copied ? "Command copied" : "Copy launch command"}
                >
                  {copied ? (
                    <Check aria-hidden="true" className="size-4" />
                  ) : (
                    <Copy aria-hidden="true" className="size-4" />
                  )}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 grid border-t border-border pt-8 md:mt-10 md:grid-cols-2 md:gap-8 md:pt-10">
          <div className="space-y-3 border-l-2 border-primary pl-5">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              For developers
            </p>
            <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
              Evaluate it on one repository.
            </h3>
            <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
              Run locally, keep the plan in the workspace, and review the resulting
              patch before you decide whether to commit it.
            </p>
            <a
              href="/start/developer"
              className="inline-flex items-center gap-2 font-body text-sm font-medium leading-6 text-primary"
            >
              Start a local run
              <ArrowRight aria-hidden="true" className="size-4" />
            </a>
          </div>

          <div className="mt-8 space-y-3 border-l-2 border-primary pl-5 md:mt-0">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.1em] text-primary">
              For organizations
            </p>
            <h3 className="font-display text-xl font-semibold leading-7 tracking-[-0.02em] text-foreground md:text-2xl md:leading-8">
              Define the review boundary for a team.
            </h3>
            <p className="font-body text-sm font-normal leading-6 text-muted-foreground">
              Configure repository access, approval requirements, and retained run
              traces before inviting engineers into a shared workspace.
            </p>
            <a
              href="/start/organization"
              className="inline-flex items-center gap-2 font-body text-sm font-medium leading-6 text-primary"
            >
              Set up an organization
              <ArrowRight aria-hidden="true" className="size-4" />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
