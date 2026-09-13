"use client";

import { motion, useReducedMotion } from "motion/react";

const ease = [0.4, 0, 0.2, 1] as const;

export default function Cta() {
  const reduceMotion = useReducedMotion();
  const rise = reduceMotion ? 0 : 11;

  return (
    <section
      className="relative min-h-screen overflow-hidden bg-muted py-32 md:py-48"
      aria-labelledby="licensing-heading"
    >
      <figure
        className="absolute inset-0 overflow-hidden rounded-lg ring-1 ring-inset ring-border/70"
        aria-label="Cinematic open-world production environment"
      >
        <img
          src="https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=2400&q=85"
          alt="Cinematic mountain environment used as a production-target scene reference"
          className="h-full w-full object-cover"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,oklch(0.12_0.012_250_/_0.72)_100%)]"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-[42%] w-px bg-primary/90 bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_24px,oklch(0.72_0.16_218_/_0.8)_24px,oklch(0.72_0.16_218_/_0.8)_25px,transparent_25px,transparent_32px)]"
        />
        <figcaption className="absolute bottom-8 left-6 max-w-[calc(100%-3rem)] font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
          World streaming target · PC · PlayStation 5 · Xbox Series X|S
        </figcaption>
      </figure>

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.07] mix-blend-screen bg-[repeating-linear-gradient(0deg,transparent_0,transparent_3px,oklch(0.74_0.018_240)_3px,oklch(0.74_0.018_240)_4px)]"
      />

      <div className="relative z-10 flex min-h-[calc(100vh-16rem)] items-center justify-center px-6 md:min-h-[calc(100vh-24rem)]">
        <div className="mx-auto max-w-3xl text-center">
          <motion.div
            initial={{ opacity: 0.27, y: rise }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.1, margin: "-80px" }}
            transition={{ duration: 0.2, ease }}
          >
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
              Studio licensing for AAA teams.
            </p>

            <h2
              id="licensing-heading"
              className="mt-4 font-display text-5xl font-semibold leading-[0.92] tracking-[-0.045em] text-foreground md:text-7xl lg:text-8xl"
            >
              Build your next world on Meridian.
            </h2>
          </motion.div>

          <motion.div
            className="mx-auto mt-8 max-w-xl space-y-4"
            initial={{ opacity: 0, y: rise }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.1, margin: "-80px" }}
            transition={{ duration: 0.2, delay: 0.06, ease }}
          >
            <p className="font-body text-base font-normal leading-7 tracking-[-0.01em] text-muted-foreground md:text-lg">
              A real-time engine for AAA production, shipping on PC,
              PlayStation 5, and Xbox Series X|S.
            </p>
            <p className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground">
              Evaluate Meridian for your next title.
            </p>
          </motion.div>

          <motion.div
            className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
            initial={{ opacity: 0, y: rise }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.1, margin: "-80px" }}
            transition={{ duration: 0.2, delay: 0.14, ease }}
          >
            <motion.a
              href="#studio-license"
              className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-6 py-3 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-primary-foreground shadow-sm sm:w-auto"
              whileHover={reduceMotion ? undefined : { y: -2 }}
              transition={{ duration: 0.3, ease }}
            >
              Request a studio license
            </motion.a>

            <motion.a
              href="#technical-docs"
              className="inline-flex w-full items-center justify-center rounded-lg border border-border px-6 py-3 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground shadow-sm sm:w-auto"
              whileHover={
                reduceMotion
                  ? undefined
                  : { y: -2, borderColor: "var(--primary)" }
              }
              transition={{ duration: 0.3, ease }}
            >
              Read technical docs
            </motion.a>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
