"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";

const headlineWords = ["Build", "open", "worlds", "without", "compromise."];

export default function Hero() {
  const reduceMotion = useReducedMotion();
  const transition = { duration: 0.3, ease: [0.4, 0, 0.2, 1] as const };

  return (
    <section className="bg-background min-h-[89vh] py-12 md:py-16">
      <div className="mx-auto max-w-[1282px] px-6">
        <div className="grid items-end gap-8 lg:grid-cols-12">
          <motion.div
            className="self-end lg:order-1 lg:col-span-6"
            initial={{ y: reduceMotion ? 0 : 11, opacity: 0.9 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          >
            <div className="space-y-8">
              <div className="space-y-4">
                <motion.p
                  className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary"
                  initial={{ y: reduceMotion ? 0 : 11, opacity: 0.9 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                >
                  REAL-TIME ENGINE FOR AAA PRODUCTION
                </motion.p>

                <h1 className="font-display text-5xl font-semibold leading-[0.92] tracking-[-0.045em] text-foreground md:text-7xl lg:text-7xl xl:text-8xl">
                  {headlineWords.map((word, index) => (
                    <motion.span
                      key={word}
                      className="inline-block"
                      initial={{
                        y: reduceMotion ? 0 : 11,
                        opacity: 0.9,
                      }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{
                        ...transition,
                        delay: index * 0.06,
                      }}
                    >
                      {word}
                      {index < headlineWords.length - 1 ? " " : ""}
                    </motion.span>
                  ))}
                </h1>
              </div>

              <motion.p
                className="font-body text-base font-normal leading-7 tracking-[-0.01em] text-muted-foreground md:text-lg"
                initial={{ y: reduceMotion ? 0 : 11, opacity: 0.9 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{
                  duration: 0.2,
                  delay: 0.36,
                  ease: [0.4, 0, 0.2, 1],
                }}
              >
                Meridian brings world streaming, virtualized geometry and
                physically based rendering into one production-ready engine for
                AAA titles shipping on console and PC.
              </motion.p>

              <motion.div
                className="space-y-4"
                initial={{ y: reduceMotion ? 0 : 11, opacity: 0.9 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{
                  duration: 0.2,
                  delay: 0.42,
                  ease: [0.4, 0, 0.2, 1],
                }}
              >
                <div className="flex flex-wrap gap-3">
                  <a
                    href="#studio-license"
                    className="rounded-lg bg-primary px-6 py-3 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-primary-foreground shadow-sm transition-shadow duration-300 hover:shadow-md"
                  >
                    Request a studio license
                  </a>
                  <a
                    href="#technical-docs"
                    className="rounded-lg border border-border px-6 py-3 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground shadow-sm transition-[border-color,box-shadow] duration-300 hover:border-primary hover:shadow-md"
                  >
                    Read the technical docs
                  </a>
                </div>

                <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                  PC / PlayStation 5 / Xbox Series X|S
                </p>
              </motion.div>
            </div>
          </motion.div>

          <motion.div
            className="lg:order-2 lg:col-span-6"
            initial={{ y: reduceMotion ? 0 : 11, opacity: 0.9 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{
              duration: 0.2,
              delay: 0.5,
              ease: [0.4, 0, 0.2, 1],
            }}
          >
            <div className="relative min-h-[32rem] overflow-hidden rounded-lg ring-1 ring-inset ring-border/70 md:min-h-[38rem]">
              <video
                src="/assets/hero-motion.mp4"
                autoPlay
                muted
                loop
                playsInline
                className="absolute inset-0 h-full w-full object-cover"
                aria-label="Ambient Meridian engine scene"
              />

              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,oklch(0.12_0.012_250_/_0.72)_100%)]" />

              <motion.div
                className="pointer-events-none absolute inset-y-0 left-[42%] z-10 w-px origin-top bg-primary/90"
                initial={{ scaleY: reduceMotion ? 1 : 0 }}
                animate={{ scaleY: 1 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.3,
                  delay: 0.7,
                  ease: [0.4, 0, 0.2, 1],
                }}
              >
                <div className="absolute inset-y-0 -left-1 w-3 bg-[repeating-linear-gradient(to_bottom,transparent_0,transparent_24px,oklch(0.72_0.16_218_/_0.8)_24px,oklch(0.72_0.16_218_/_0.8)_25px,transparent_25px,transparent_32px)]" />
              </motion.div>

              <div className="absolute inset-x-0 bottom-0 z-20 p-6">
                <div className="flex items-end justify-between gap-3 border-t border-border pt-4">
                  <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground">
                    A real-time open-world scene rendered in Meridian.
                  </p>
                  <p className="hidden font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary md:block">
                    WORLD STREAMING // LIVE
                  </p>
                </div>
              </div>

              <div className="absolute bottom-20 left-6 z-20 hidden w-[42%] overflow-hidden rounded-lg border border-border bg-card shadow-sm md:block">
                <Image
                  src="/assets/hero-1.png"
                  alt="Open-world environment in Meridian"
                  width={1536}
                  height={1024}
                  unoptimized
                  className="aspect-[3/2] w-full object-cover"
                />
              </div>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-8 md:hidden">
              <div className="overflow-hidden rounded-lg ring-1 ring-inset ring-border/70">
                <Image
                  src="/assets/hero-1.png"
                  alt="Open-world environment in Meridian"
                  width={1536}
                  height={1024}
                  unoptimized
                  className="aspect-[3/2] w-full object-cover"
                />
              </div>
              <div className="overflow-hidden rounded-lg ring-1 ring-inset ring-border/70">
                <Image
                  src="/assets/hero-2.png"
                  alt="Virtualized geometry detail in Meridian"
                  width={1536}
                  height={1024}
                  unoptimized
                  className="aspect-[3/2] w-full object-cover"
                />
              </div>
              <div className="col-span-2 overflow-hidden rounded-lg ring-1 ring-inset ring-border/70">
                <Image
                  src="/assets/hero-3.png"
                  alt="Physically based rendered scene in Meridian"
                  width={1536}
                  height={1024}
                  unoptimized
                  className="aspect-[3/2] w-full object-cover"
                />
              </div>
            </div>

            <div className="mt-8 hidden grid-cols-2 gap-8 md:grid">
              <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
                <Image
                  src="/assets/hero-2.png"
                  alt="Virtualized geometry detail in Meridian"
                  width={1536}
                  height={1024}
                  unoptimized
                  className="aspect-[3/2] w-full object-cover"
                />
              </div>
              <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
                <Image
                  src="/assets/hero-3.png"
                  alt="Physically based rendered scene in Meridian"
                  width={1536}
                  height={1024}
                  unoptimized
                  className="aspect-[3/2] w-full object-cover"
                />
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
