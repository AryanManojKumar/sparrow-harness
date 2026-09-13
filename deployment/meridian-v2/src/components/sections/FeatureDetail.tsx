"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";

const workflow = [
  {
    label: "Author",
    heading: "Compose the world as one connected space.",
    body: "Create and refine open-world content without breaking the experience into disconnected authoring views.",
    detail: "Editor and runtime stay connected around the same streamed world.",
    image: "/assets/feature-detail-1.png",
  },
  {
    label: "Validate",
    heading: "Validate the world in runtime context.",
    body: "Assess streaming behavior where the world runs, keeping technical decisions connected to the player experience.",
    detail: "Streaming is built into Meridian’s real-time open-world workflow.",
    image: "/assets/feature-detail-2.png",
  },
  {
    label: "Ship",
    heading: "Take the same world to console and PC.",
    body: "Carry validated world content forward into the build your team ships.",
    detail: "World content is prepared for shipping on console and PC.",
    image: "/assets/feature-detail-3.png",
  },
];

const ease = [0.4, 0, 0.2, 1] as const;

export default function FeatureDetail() {
  const [activeTab, setActiveTab] = useState(0);
  const reduceMotion = useReducedMotion();
  const activeWorkflow = workflow[activeTab];

  const rise = (delay = 0) => ({
    initial: { opacity: 0.27, y: reduceMotion ? 0 : 11 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px", amount: 0.1 },
    transition: { duration: 0.2, delay, ease },
  });

  return (
    <section className="bg-background overflow-hidden py-24 md:py-32">
      <div className="w-full">
        <div className="relative h-[44rem] overflow-hidden rounded-lg ring-1 ring-inset ring-border/70 md:h-[46rem]">
          <Image
            src="/assets/feature-detail-1.png"
            alt="A streamed open world in Meridian, viewed in its runtime context."
            fill
            unoptimized
            priority={false}
            className="object-cover"
            sizes="100vw"
          />

          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,oklch(0.12_0.012_250_/_0.72)_100%)]" />

          <motion.div
            aria-hidden="true"
            initial={{ scaleY: reduceMotion ? 1 : 0 }}
            whileInView={{ scaleY: 1 }}
            viewport={{ once: true, margin: "-80px", amount: 0.1 }}
            transition={{ duration: 0.3, delay: 0.34, ease }}
            className="pointer-events-none absolute inset-y-0 left-[42%] w-px origin-top bg-primary/90"
          >
            <div className="absolute inset-0 bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_24px,oklch(0.72_0.16_218_/_0.8)_24px,oklch(0.72_0.16_218_/_0.8)_25px,transparent_25px,transparent_32px)]" />
          </motion.div>

          <div className="absolute inset-x-0 bottom-0 bg-[linear-gradient(to_top,oklch(0.12_0.012_250_/_0.96),transparent)]">
            <div className="mx-auto max-w-[80rem] px-6 pb-24 pt-32 md:pb-32">
              <motion.div {...rise(0)} className="max-w-2xl space-y-4">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                  Open-world streaming
                </p>
                <h2 className="font-display text-3xl font-semibold leading-[1] tracking-[-0.035em] text-foreground md:text-5xl">
                  Build seamless worlds in the same reality you ship.
                </h2>
              </motion.div>
              <motion.p
                {...rise(0.06)}
                className="mt-8 max-w-2xl font-body text-base font-normal leading-7 tracking-[-0.01em] text-muted-foreground md:text-lg"
              >
                Meridian keeps open-world authoring, validation, and runtime behavior aligned, so AAA teams can move from editor work to a shipping build without treating them as separate worlds. Stream expansive environments for console and PC from one real-time engine.
              </motion.p>
            </div>
          </div>
        </div>

        <motion.aside
          {...rise(0.14)}
          className="relative z-10 -mt-12 ml-6 max-w-xl rounded-lg border border-border bg-card/95 p-5 shadow-md backdrop-blur-sm md:-mt-20 md:ml-12"
          aria-label="Open-world workflow inspection"
        >
          <div className="grid gap-8 md:grid-cols-3">
            <div className="space-y-4">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                SYSTEM
              </p>
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Editor + runtime
              </p>
            </div>
            <div className="space-y-4">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                WORLD STATE
              </p>
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Streamed context
              </p>
            </div>
            <div className="space-y-4">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                BUILD TARGETS
              </p>
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-accent">
                PC · PlayStation 5 · Xbox Series X|S
              </p>
            </div>
          </div>
        </motion.aside>
      </div>

      <div className="mx-auto max-w-[80rem] px-6 pt-24 md:pt-32">
        <div className="grid gap-8 lg:grid-cols-12">
          <motion.div {...rise(0)} className="space-y-8 lg:col-span-4">
            <div className="space-y-4">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Connected workflow
              </p>
              <p className="font-body text-base font-normal leading-7 tracking-[-0.01em] text-foreground md:text-lg">
                A continuous workflow for authoring, validating, and shipping streamed open worlds.
              </p>
            </div>

            <div
              role="tablist"
              aria-label="Open-world workflow stages"
              className="flex gap-3 overflow-x-auto pb-4"
            >
              {workflow.map((item, index) => (
                <button
                  key={item.label}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === index}
                  aria-controls={`workflow-panel-${index}`}
                  id={`workflow-tab-${index}`}
                  onClick={() => setActiveTab(index)}
                  className={`shrink-0 rounded-full border p-5 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] transition-colors duration-300 ${
                    activeTab === index
                      ? "border-primary bg-primary text-primary-foreground shadow-sm"
                      : "border-border bg-card text-muted-foreground hover:border-primary hover:text-foreground"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="border-t border-border pt-8">
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                Technical detail
              </p>
              <p className="mt-4 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground">
                {activeWorkflow.detail}
              </p>
            </div>
          </motion.div>

          <motion.div
            {...rise(0.14)}
            id={`workflow-panel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`workflow-tab-${activeTab}`}
            className="lg:col-span-8"
          >
            <motion.article
              key={activeWorkflow.label}
              initial={{ opacity: 0.7, y: reduceMotion ? 0 : 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease }}
              whileHover={{ y: reduceMotion ? 0 : -2 }}
              className="overflow-hidden rounded-lg border border-border bg-card shadow-sm transition-[border-color,box-shadow] duration-300 hover:border-primary hover:shadow-md"
            >
              <div className="relative aspect-[3/2] overflow-hidden">
                {activeTab === 2 && (
                  <div className="absolute -right-24 -top-24 z-10 h-72 w-72 rounded-full bg-accent/20 blur-3xl" />
                )}
                <Image
                  src={activeWorkflow.image}
                  alt="A streamed open world in Meridian, viewed in its runtime context."
                  fill
                  unoptimized
                  className="object-cover"
                  sizes="(min-width: 1024px) 66vw, 100vw"
                />
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,oklch(0.12_0.012_250_/_0.72)_100%)]" />
                <div className="pointer-events-none absolute inset-y-0 left-[42%] w-px bg-primary/90 opacity-60">
                  <div className="absolute inset-0 bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_24px,oklch(0.72_0.16_218_/_0.8)_24px,oklch(0.72_0.16_218_/_0.8)_25px,transparent_25px,transparent_32px)]" />
                </div>
              </div>

              <div className="space-y-4 p-5">
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                  {activeWorkflow.label}
                </p>
                <h3 className="font-display text-xl font-semibold leading-tight tracking-[-0.02em] text-foreground md:text-2xl">
                  {activeWorkflow.heading}
                </h3>
                <p className="font-body text-base font-normal leading-7 tracking-[-0.01em] text-muted-foreground md:text-lg">
                  {activeWorkflow.body}
                </p>
                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                  A streamed open world in Meridian, viewed in its runtime context.
                </p>
              </div>
            </motion.article>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
