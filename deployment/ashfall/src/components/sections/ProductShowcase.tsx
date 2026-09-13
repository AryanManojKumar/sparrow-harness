"use client";

import Image from "next/image";
import { useState } from "react";
import { motion } from "motion/react";

const ease = [0.06, 0.81, 0, 0.98] as const;

const beats = [
  {
    title: "A CITY IN COLLAPSE",
    body: "Ashfall begins where the city breaks beneath the volcano.",
    image: "/assets/product-showcase-2.png",
    alt: "Campaign gameplay capture in a devastated volcanic city",
    label: "CAMPAIGN",
  },
  {
    title: "THE STORY CAMPAIGN",
    body: "Enter the story at the heart of the collapse.",
    image: "/assets/product-showcase-2.png",
    alt: "Story campaign gameplay capture in the collapsing city",
    label: "CAMPAIGN",
  },
  {
    title: "32-PLAYER EXTRACTION",
    body: "Step into extraction as the city comes apart.",
    image: "/assets/product-showcase-3.png",
    alt: "Extraction mode gameplay capture during an evacuation objective",
    label: "32-PLAYER EXTRACTION MODE",
  },
];

export default function ProductShowcase() {
  const [trailerHovered, setTrailerHovered] = useState(false);

  return (
    <section className="bg-background py-24 md:py-32">
      <div className="relative isolate overflow-hidden bg-background">
        <motion.div
          className="relative mx-auto w-full max-w-[88rem] px-6"
          initial={{ opacity: 0, y: 17 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px", amount: 0.01 }}
          transition={{ duration: 0.5, ease }}
        >
          <motion.div
            className="group relative z-20 aspect-[3/2] overflow-hidden rounded-sm border border-border bg-card"
            onHoverStart={() => setTrailerHovered(true)}
            onHoverEnd={() => setTrailerHovered(false)}
            animate={{ y: trailerHovered ? -2 : 0 }}
            transition={{ duration: 0.3, ease }}
          >
            <Image
              src="/assets/product-showcase-1.png"
              alt="Reveal trailer poster showing Ashfall's volcanic city collapsing"
              fill
              priority={false}
              unoptimized
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 88rem"
            />

            <div className="absolute inset-0 bg-background/35" />

            <motion.div
              className="absolute inset-y-0 right-[14%] w-[18%] bg-primary [clip-path:polygon(42%_0,58%_0,100%_100%,78%_100%)] opacity-90"
              animate={{ opacity: trailerHovered ? 1 : 0.9 }}
              transition={{ duration: 1, ease }}
            />
            <motion.div
              className="absolute inset-y-0 right-[16%] w-[2px] bg-accent"
              animate={{ opacity: trailerHovered ? 1 : 0.7 }}
              transition={{ duration: 1, ease }}
            />

            <div className="absolute inset-x-0 bottom-10 bg-[linear-gradient(0deg,oklch(0.12_0.025_250_/_0.94)_0%,transparent_100%)] px-6 py-8 md:bottom-16 md:px-12 md:py-12">
              <div className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
                  REVEAL TRAILER
                </p>
                <h2 className="font-display text-4xl font-bold uppercase leading-[0.9] tracking-[-0.03em] text-foreground md:text-6xl">
                  WHEN THE CITY FALLS
                </h2>
              </div>
            </div>

            <button
              type="button"
              aria-label="PLAY"
              className="absolute left-6 top-6 flex size-12 items-center justify-center rounded-full border border-foreground bg-background/85 font-body text-sm font-medium leading-5 text-foreground md:left-12 md:top-12"
            >
              ▶
            </button>

            <div className="absolute inset-x-0 bottom-0 bg-background/85 px-4 py-3 text-foreground">
              <span className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em]">
                REVEAL TRAILER · PLAY
              </span>
            </div>

            <div className="absolute inset-y-0 right-0 w-1 bg-primary" />
          </motion.div>
        </motion.div>

        <motion.div
          className="relative z-30 -mt-10 mx-6 border border-accent/40 bg-primary px-6 py-8 text-primary-foreground rounded-sm md:-mt-16 md:mx-auto md:max-w-4xl md:px-12 md:py-12"
          initial={{ opacity: 0, y: 17 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px", amount: 0.01 }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <div className="space-y-8">
            <div className="space-y-4">
              <p className="font-display text-xs font-semibold uppercase leading-4 tracking-[0.14em]">
                ASHFALL
              </p>
              <p className="font-body text-base font-normal leading-7 md:text-lg">
                A first-person shooter set in a collapsing volcanic city. A
                story campaign. A 32-player extraction mode.
              </p>
            </div>

            <div className="space-y-8 border-t border-primary-foreground/40 pt-8">
              {beats.map((beat, index) => (
                <motion.article
                  key={beat.title}
                  className="space-y-4"
                  initial={{ opacity: 0, y: 17 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px", amount: 0.01 }}
                  transition={{ duration: 0.5, delay: 0.1 + index * 0.1, ease }}
                >
                  <div className="relative aspect-[3/2] overflow-hidden rounded-sm border border-border bg-card">
                    <Image
                      src={beat.image}
                      alt={beat.alt}
                      fill
                      unoptimized
                      className="object-cover"
                      sizes="(max-width: 768px) calc(100vw - 72px), 48rem"
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-background/85 px-4 py-3 text-foreground">
                      <span className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em]">
                        {beat.label}
                      </span>
                    </div>
                    <div className="absolute inset-y-0 right-0 w-1 bg-primary" />
                  </div>
                  <div className="space-y-4">
                    <h3 className="font-display text-2xl font-bold uppercase leading-none tracking-[-0.02em] text-primary-foreground md:text-3xl">
                      {beat.title}
                    </h3>
                    <p className="font-body text-base font-normal leading-7 md:text-lg">
                      {beat.body}
                    </p>
                  </div>
                </motion.article>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
