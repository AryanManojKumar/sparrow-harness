"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";

const fallbackImage =
  "/assets/product-showcase-1.png";

const showcases = [
  {
    project: "Project / 01",
    title: "Death Stranding Director’s Cut",
    studio: "Kojima Productions",
    image: fallbackImage,
  },
  {
    project: "Project / 02",
    title: "Horizon Forbidden West",
    studio: "Guerrilla",
    image: "/assets/product-showcase-2.png",
  },
  {
    project: "Project / 03",
    title: "Ratchet & Clank: Rift Apart",
    studio: "Insomniac Games",
    image: "/assets/product-showcase-3.png",
  },
  {
    project: "Project / 04",
    title: "Returnal",
    studio: "Housemarque",
    image: "/assets/product-showcase-4.png",
  },
];

export default function ProductShowcase() {
  const reduceMotion = useReducedMotion();
  const rise = reduceMotion ? 0 : 11;
  const cardLift = reduceMotion ? 0 : -2;

  return (
    <section className="relative overflow-hidden bg-muted py-24 md:py-32">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.07] mix-blend-screen bg-[repeating-linear-gradient(0deg,transparent_0,transparent_3px,oklch(0.74_0.018_240)_3px,oklch(0.74_0.018_240)_4px)]"
      />

      <div className="relative mx-auto max-w-[88rem] px-6">
        <div className="space-y-8">
          <div className="max-w-6xl space-y-4">
            <motion.div
              initial={{ opacity: 0.27, y: rise }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px", amount: 0.1 }}
              transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
              className="space-y-4"
            >
              <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                Production showcases
              </p>
              <h2 className="font-display text-3xl font-semibold leading-[1] tracking-[-0.035em] text-foreground md:text-5xl">
                Built for the productions that define their worlds.
              </h2>
            </motion.div>

            <motion.div
              initial={{ opacity: 0.27, y: rise }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px", amount: 0.1 }}
              transition={{
                duration: 0.2,
                delay: 0.06,
                ease: [0.4, 0, 0.2, 1],
              }}
              className="space-y-8"
            >
              <p className="max-w-6xl font-body text-base font-normal leading-7 tracking-[-0.01em] text-muted-foreground md:text-lg">
                Meridian brings real-time open-world streaming, virtualized
                geometry, and physically based rendering into one engine for AAA
                production. It ships on PC, PlayStation 5, and Xbox Series X|S.
              </p>

              <div className="flex flex-wrap gap-3">
                <a
                  href="#"
                  className="rounded-lg border border-primary bg-primary px-6 py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary-foreground shadow-sm transition-shadow duration-300 hover:shadow-md"
                >
                  Request a studio license
                </a>
                <a
                  href="#"
                  className="rounded-lg border border-border px-6 py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground shadow-sm transition-colors duration-300 hover:border-primary hover:shadow-md"
                >
                  Read technical docs
                </a>
              </div>
            </motion.div>
          </div>

          <div className="grid gap-8 md:grid-cols-2">
            {showcases.map((showcase, index) => (
              <motion.article
                key={showcase.title}
                initial={{ opacity: 0.27, y: rise }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px", amount: 0.1 }}
                transition={{
                  duration: 0.2,
                  delay: 0.14 + index * 0.05,
                  ease: [0.4, 0, 0.2, 1],
                }}
              >
                <motion.div
                  whileHover={{
                    y: cardLift,
                    borderColor: "var(--primary)",
                  }}
                  transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                  className="overflow-hidden rounded-lg border border-border bg-card shadow-sm"
                >
                  <div className="relative aspect-[4/3] overflow-hidden ring-1 ring-inset ring-border/70">
                    <Image
                      src={showcase.image}
                      alt={`${showcase.title} production showcase`}
                      fill
                      unoptimized
                      sizes="(min-width: 768px) 50vw, 100vw"
                      className="object-cover"
                      onError={(event) => {
                        if (event.currentTarget.src !== fallbackImage) {
                          event.currentTarget.src = fallbackImage;
                        }
                      }}
                    />
                    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,oklch(0.12_0.012_250_/_0.72)_100%)]" />
                    <div
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-y-0 left-[42%] w-px bg-primary/90 bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_24px,oklch(0.72_0.16_218_/_0.8)_24px,oklch(0.72_0.16_218_/_0.8)_25px,transparent_25px,transparent_32px)]"
                    />
                  </div>

                  <div className="space-y-4 px-6 py-5">
                    <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                      {showcase.project}
                    </p>
                    <h3 className="font-display text-xl font-semibold leading-tight tracking-[-0.02em] text-foreground md:text-2xl">
                      {showcase.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                        Studio credit
                      </span>
                      <span className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground">
                        {showcase.studio}
                      </span>
                    </div>
                    <a
                      href="#"
                      className="inline-flex font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary transition-colors duration-300 hover:text-foreground"
                    >
                      View case study
                    </a>
                  </div>
                </motion.div>
              </motion.article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
