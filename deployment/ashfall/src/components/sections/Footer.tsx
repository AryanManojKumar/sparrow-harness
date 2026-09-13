"use client";

import { motion, useReducedMotion } from "motion/react";

const platformLine = "PlayStation 5, Xbox Series X|S, and PC.";

function ArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4 shrink-0"
      fill="none"
      viewBox="0 0 16 16"
    >
      <path
        d="M3 8h9M8.5 3.5 13 8l-4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function UtilityLink({
  children,
  href = "#",
}: {
  children: React.ReactNode;
  href?: string;
}) {
  const reducedMotion = useReducedMotion();

  return (
    <motion.a
      href={href}
      className="inline-flex items-center gap-3 font-body text-sm font-medium leading-5 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
      whileHover={reducedMotion ? undefined : { y: -2 }}
      transition={{ duration: 0.3, ease: [0.06, 0.81, 0, 0.98] }}
    >
      <span>{children}</span>
      <ArrowIcon />
    </motion.a>
  );
}

export default function Footer() {
  const reducedMotion = useReducedMotion();
  const entrance = {
    opacity: 1,
    y: reducedMotion ? 0 : 17,
  };

  return (
    <section
      className="bg-muted bg-[repeating-linear-gradient(118deg,transparent_0,transparent_34px,oklch(0.34_0.03_250_/_0.24)_35px,transparent_37px)] py-12 md:py-16"
      aria-label="ASHFALL site footer"
    >
      <div className="relative z-10 mx-auto max-w-6xl px-6">
        <motion.div
          initial={entrance}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px", amount: 0.01 }}
          transition={{ duration: 0.5, ease: [0.06, 0.81, 0, 0.98] }}
          className="space-y-8"
        >
          <div className="grid gap-8 md:grid-cols-2">
            <div className="space-y-4">
              <a
                href="#top"
                className="inline-flex items-center gap-3 text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
                aria-label="ASHFALL — back to top"
              >
                <span
                  aria-hidden="true"
                  className="h-8 w-8 shrink-0 bg-foreground"
                  style={{
                    maskImage:
                      "url('/assets/nav-logo.png')",
                    maskPosition: "center",
                    maskRepeat: "no-repeat",
                    maskSize: "contain",
                    WebkitMaskImage:
                      "url('/assets/nav-logo.png')",
                    WebkitMaskPosition: "center",
                    WebkitMaskRepeat: "no-repeat",
                    WebkitMaskSize: "contain",
                  }}
                />
                <span className="font-display text-2xl font-bold uppercase leading-none tracking-[-0.02em]">
                  ASHFALL
                </span>
              </a>

              <div className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
                  Platforms
                </p>
                <p className="font-body text-sm font-medium leading-5 text-foreground">
                  {platformLine}
                </p>
                <p className="font-body text-sm font-medium leading-5 text-muted-foreground">
                  Release date: To be announced
                </p>
              </div>
            </div>

            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
              <nav aria-label="Explore" className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
                  Explore
                </p>
                <div className="flex flex-col items-start gap-3">
                  <UtilityLink href="#game">Game</UtilityLink>
                  <UtilityLink href="#media">Media</UtilityLink>
                  <UtilityLink href="#news">News</UtilityLink>
                </div>
              </nav>

              <nav aria-label="Support" className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
                  Support
                </p>
                <div className="flex flex-col items-start gap-3">
                  <UtilityLink>Support</UtilityLink>
                  <UtilityLink>Accessibility</UtilityLink>
                  <UtilityLink>Contact</UtilityLink>
                </div>
              </nav>

              <nav aria-label="Company" className="space-y-4">
                <p className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground">
                  Company
                </p>
                <div className="flex flex-col items-start gap-3">
                  <UtilityLink>About</UtilityLink>
                  <UtilityLink>Careers</UtilityLink>
                  <UtilityLink>Press</UtilityLink>
                </div>
              </nav>
            </div>
          </div>

          <motion.div
            initial={entrance}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px", amount: 0.01 }}
            transition={{
              duration: 0.5,
              delay: 0.1,
              ease: [0.06, 0.81, 0, 0.98],
            }}
            className="border-t border-border pt-8"
          >
            <div className="flex flex-wrap items-center gap-3">
              <span
                aria-hidden="true"
                className="inline-flex h-8 w-8 items-center justify-center border border-border text-muted-foreground"
              >
                <svg fill="none" viewBox="0 0 20 20" className="h-4 w-4">
                  <path
                    d="m3 15 5-10 2 6 2-3 5 7H3Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </span>

              <nav
                aria-label="Social destinations"
                className="flex flex-wrap items-center gap-3"
              >
                <UtilityLink>YouTube</UtilityLink>
                <UtilityLink>Discord</UtilityLink>
                <UtilityLink>X</UtilityLink>
              </nav>

              <span className="font-body text-sm font-medium leading-5 text-muted-foreground">
                © ASHFALL. All rights reserved.
              </span>

              <nav
                aria-label="Legal information"
                className="flex flex-wrap items-center gap-3"
              >
                <UtilityLink>Terms of Use</UtilityLink>
                <UtilityLink>Privacy Policy</UtilityLink>
                <UtilityLink>Cookie Policy</UtilityLink>
                <UtilityLink>Your Privacy Choices</UtilityLink>
              </nav>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
