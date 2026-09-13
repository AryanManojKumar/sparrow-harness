"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";

const ease = [0.06, 0.81, 0, 0.98] as const;

function EvidenceFrame({
  src,
  alt,
  caption,
  className = "",
  priority = false,
  fault = false,
}: {
  src: string;
  alt: string;
  caption: string;
  className?: string;
  priority?: boolean;
  fault?: boolean;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.figure
      className={`group relative overflow-hidden rounded-sm border border-border bg-card after:absolute after:inset-y-0 after:right-0 after:z-20 after:w-1 after:bg-primary ${className}`}
      initial={{ opacity: 0, y: reduceMotion ? 0 : 17 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px", amount: 0.1 }}
      transition={{ duration: 0.5, ease }}
      whileHover={reduceMotion ? undefined : { y: -2 }}
    >
      <div className="relative aspect-[3/2] overflow-hidden">
        <Image
          src={src}
          alt={alt}
          fill
          priority={priority}
          unoptimized
          sizes="(min-width: 1024px) 62vw, 100vw"
          className="object-cover transition-transform duration-300 ease-[cubic-bezier(0.06,0.81,0,0.98)] group-hover:scale-[1.02]"
        />
        {fault ? (
          <>
            <div className="pointer-events-none absolute inset-y-0 right-[14%] z-10 w-[18%] bg-primary opacity-90 [clip-path:polygon(42%_0,58%_0,100%_100%,78%_100%)]" />
            <div className="pointer-events-none absolute inset-y-0 right-[16%] z-20 w-[2px] bg-accent" />
          </>
        ) : null}
      </div>
      <figcaption className="absolute inset-x-0 bottom-0 z-30 bg-background/85 px-4 py-3 font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-foreground">
        {caption}
      </figcaption>
    </motion.figure>
  );
}

function RouteDiagram() {
  return (
    <div className="rounded-sm border border-border bg-card px-6 py-8">
      <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
        Extraction route
      </p>
      <svg
        viewBox="0 0 360 132"
        className="mt-4 h-auto w-full text-primary"
        aria-label="Extraction route and shifting danger zones"
        role="img"
      >
        <path
          d="M24 108 C77 92 85 40 140 53 S203 108 243 70 S295 35 336 22"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeDasharray="8 7"
        />
        <circle cx="24" cy="108" r="9" fill="currentColor" />
        <circle
          cx="140"
          cy="53"
          r="23"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          opacity="0.7"
        />
        <circle
          cx="140"
          cy="53"
          r="36"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.35"
        />
        <path
          d="M325 13 L344 22 L325 31 Z"
          fill="currentColor"
          className="text-accent"
        />
        <path
          d="M226 82 L244 64 L262 82 L244 100 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        />
        <path
          d="M58 121 H305"
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.35"
        />
      </svg>
    </div>
  );
}

export default function FeatureDetail() {
  const reduceMotion = useReducedMotion();

  const copyEntrance = {
    initial: { opacity: 0, y: reduceMotion ? 0 : 17 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px", amount: 0.1 },
    transition: { duration: 0.5, ease },
  };

  return (
    <section className="bg-muted bg-[repeating-linear-gradient(118deg,transparent_0,transparent_34px,oklch(0.34_0.03_250_/_0.24)_35px,transparent_37px)] py-24 md:py-32">
      <div className="relative z-10 mx-auto max-w-[88rem] px-6">
        <div className="flex flex-col gap-8">
          <EvidenceFrame
            src="/assets/feature-detail-1.png"
            alt="ASHFALL reveal trailer gameplay frame showing a squad crossing a collapsing volcanic city district"
            caption="FRAME 01 — A CITY IN COLLAPSE"
            priority
            fault
            className="order-2 lg:order-1 lg:col-span-8 lg:col-start-3"
          />

          <div className="order-1 lg:order-2 lg:col-span-6 lg:col-start-3">
            <motion.div
              {...copyEntrance}
              transition={{ duration: 0.5, ease, delay: 0.1 }}
              className="space-y-4"
            >
              <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-accent">
                EXTRACTION UNDER ASH
              </p>
              <h2 className="font-display text-4xl font-bold uppercase leading-[0.9] tracking-[-0.03em] text-foreground md:text-6xl">
                THE CITY IS FALLING. GET OUT.
              </h2>
            </motion.div>

            <motion.div
              {...copyEntrance}
              transition={{ duration: 0.5, ease, delay: 0.2 }}
              className="mt-8 space-y-4"
            >
              <p className="font-body text-base font-normal leading-7 text-muted-foreground md:text-lg">
                ASHFALL puts 32 players inside a collapsing volcanic city, where
                getting out is the fight.
              </p>
              <p className="font-body text-sm font-medium leading-5 text-muted-foreground">
                Release date: To be announced
              </p>
            </motion.div>
          </div>

          <div className="order-3 grid gap-8 lg:grid-cols-12">
            <EvidenceFrame
              src="/assets/feature-detail-1.png"
              alt="Campaign gameplay frame showing a squad crossing a volcanic city district"
              caption="FRAME 02 — COLLAPSE CROSSING"
              className="lg:col-span-7"
            />

            <motion.div
              {...copyEntrance}
              transition={{ duration: 0.5, ease, delay: 0.1 }}
              className="self-end rounded-sm border border-border bg-card px-6 py-8 lg:col-span-4 lg:col-start-9"
            >
              <div className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
                  32-player extraction mode
                </p>
                <RouteDiagram />
              </div>
            </motion.div>
          </div>

          <div className="order-4 grid gap-8 lg:grid-cols-12">
            <motion.div
              {...copyEntrance}
              transition={{ duration: 0.5, ease, delay: 0.1 }}
              className="self-end rounded-sm border border-border bg-card px-6 py-8 lg:col-span-4"
            >
              <div className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-accent">
                  32-player extraction mode
                </p>
                <p className="font-display text-2xl font-bold uppercase leading-none tracking-[-0.02em] text-foreground md:text-3xl">
                  32-PLAYER EXTRACTION
                </p>
              </div>
            </motion.div>

            <EvidenceFrame
              src="/assets/feature-detail-2.png"
              alt="Gameplay frame showing players moving through a volcanic-city hazard zone"
              caption="FRAME 03 — SHIFTING HAZARD ZONES"
              className="lg:col-span-7 lg:col-start-6"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
