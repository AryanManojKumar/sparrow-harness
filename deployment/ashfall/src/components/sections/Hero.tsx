"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";

const premiseWords = ["THE", "CITY", "FALLS.", "YOU", "FIGHT", "ON."];

export default function Hero() {
  const reduceMotion = useReducedMotion();
  const entranceY = reduceMotion ? 0 : 17;

  return (
    <section
      id="top"
      className="group relative isolate min-h-[calc(100svh-64px)] w-full overflow-hidden bg-background text-foreground"
      aria-labelledby="ashfall-title"
    >
      <Image
        src="/assets/hero-1.png"
        alt=""
        fill
        priority
        unoptimized
        className="absolute inset-0 h-full w-full object-cover opacity-70"
      />
      <Image
        src="/assets/hero-2.png"
        alt=""
        fill
        priority
        unoptimized
        className="absolute inset-0 hidden h-full w-full object-cover opacity-70 max-md:block"
      />
      <video
        src="/assets/hero-motion.mp4"
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 h-full w-full object-cover opacity-70"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,oklch(0.12_0.025_250_/_0.94)_0%,oklch(0.12_0.025_250_/_0.52)_52%,oklch(0.12_0.025_250_/_0.78)_100%)]" />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-[14%] z-[1] w-[18%] bg-primary opacity-90 [clip-path:polygon(42%_0,58%_0,100%_100%,78%_100%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-[16%] z-[2] w-[2px] bg-accent opacity-80 transition-opacity duration-1000 group-hover:opacity-100"
      />

      <div className="relative z-10 flex min-h-[calc(100svh-64px)] items-center justify-center px-6 py-24 md:py-32">
        <div className="w-full max-w-[36rem] text-center">
          <motion.div
            className="relative z-20"
            initial={{ y: entranceY }}
            animate={{ y: 0 }}
            transition={{
              duration: 0.5,
              ease: [0.06, 0.81, 0, 0.98],
            }}
          >
            <svg
              viewBox="0 0 720 126"
              role="img"
              aria-labelledby="ashfall-logo-title"
              className="mx-auto w-full text-foreground"
            >
              <title id="ashfall-logo-title">ASHFALL</title>
              <path
                d="M22 108 73 18h30L52 108H22Zm59 0 50-90h28l-20 36 19 54h-29l-13-39-22 39H65Z"
                fill="currentColor"
              />
              <path
                d="M176 18h29v66h52v24h-81V18Z"
                fill="currentColor"
              />
              <path
                d="M325 14c38 0 68 21 68 49s-30 49-68 49-68-21-68-49 30-49 68-49Zm0 23c-21 0-38 11-38 26s17 26 38 26 38-11 38-26-17-26-38-26Z"
                fill="currentColor"
              />
              <path
                d="M423 18h78v21h-49v16h41v18h-41v35h-29V18Z"
                fill="currentColor"
              />
              <path
                d="M527 18h29l41 51V18h28v90h-28l-42-52v52h-28V18Z"
                fill="currentColor"
              />
              <path
                d="M650 18h29v90h-29V18Zm43 0h27v90h-27V18Z"
                fill="currentColor"
              />
            </svg>
            <h1 id="ashfall-title" className="sr-only">
              ASHFALL
            </h1>
          </motion.div>

          <motion.h2
            className="mt-8 font-display text-2xl font-bold uppercase leading-none tracking-[-0.02em] md:text-3xl"
            initial={{ y: entranceY }}
            animate={{ y: 0 }}
            transition={{
              delay: 0.15,
              duration: 0.5,
              ease: [0.06, 0.81, 0, 0.98],
            }}
          >
            {premiseWords.map((word, index) => (
              <motion.span
                key={index}
                className="inline-block"
                initial={{ y: entranceY }}
                animate={{ y: 0 }}
                transition={{
                  delay: 0.15 + index * 0.07,
                  duration: 0.5,
                  ease: [0.06, 0.81, 0, 0.98],
                }}
              >
                {word}
                {index < premiseWords.length - 1 ? "\u00A0" : ""}
              </motion.span>
            ))}
          </motion.h2>

          <motion.p
            className="mt-4 font-body text-base font-normal leading-7 text-muted-foreground md:text-lg"
            initial={{ y: entranceY }}
            animate={{ y: 0 }}
            transition={{
              delay: 0.35,
              duration: 0.5,
              ease: [0.06, 0.81, 0, 0.98],
            }}
          >
            Story campaign and 32-player extraction on PlayStation 5, Xbox Series
            X|S, and PC.
          </motion.p>

          <motion.div
            className="mt-8 flex flex-col items-center space-y-4"
            initial={{ y: entranceY }}
            animate={{ y: 0 }}
            transition={{
              delay: 0.45,
              duration: 0.5,
              ease: [0.06, 0.81, 0, 0.98],
            }}
          >
            <motion.a
              href="#pre-order"
              whileHover={{ y: reduceMotion ? 0 : -2 }}
              transition={{
                duration: 0.3,
                ease: [0.06, 0.81, 0, 0.98],
              }}
              className="rounded-sm border border-accent/40 bg-primary px-6 py-4 font-body text-sm font-medium leading-5 text-primary-foreground"
            >
              Pre-order now
            </motion.a>
            <a
              href="#reveal-trailer"
              className="border-b border-border pb-1 font-body text-sm font-medium leading-5 text-foreground transition-colors hover:text-accent"
            >
              Watch the reveal trailer
            </a>
          </motion.div>
        </div>
      </div>

      <motion.aside
        className="absolute bottom-0 left-0 z-10 max-w-[36rem] border-t border-border bg-background/85 px-6 py-8 text-left md:py-8"
        initial={{ y: entranceY }}
        animate={{ y: 0 }}
        transition={{
          delay: 0.55,
          duration: 0.5,
          ease: [0.06, 0.81, 0, 0.98],
        }}
      >
        <div className="space-y-4">
          <div>
            <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
              Platforms
            </p>
            <p className="font-body text-sm font-medium leading-5 text-foreground">
              PlayStation 5, Xbox Series X|S, and PC.
            </p>
          </div>
          <p className="font-body text-sm font-medium leading-5 text-muted-foreground">
            Release date: To be announced
          </p>
        </div>
      </motion.aside>
    </section>
  );
}
