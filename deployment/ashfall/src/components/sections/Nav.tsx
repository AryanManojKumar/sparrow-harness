"use client";

import { motion, useReducedMotion } from "motion/react";

const navItems = [
  { label: "Campaign", href: "#campaign" },
  { label: "Extraction", href: "#extraction" },
  { label: "Media", href: "#media" },
  { label: "Platforms", href: "#platforms" },
  { label: "Release date", href: "#release-date" },
  { label: "Pre-order", href: "#preorder" },
] as const;
const platforms = ["PlayStation 5", "Xbox Series X|S", "PC"] as const;

export default function Nav() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="sticky top-0 z-50 border-b border-border bg-background">
      <div className="mx-auto flex max-w-[88rem] items-center justify-between px-6 py-4">
        <a
          href="#top"
          aria-label="ASHFALL — back to top"
          className="flex shrink-0 items-center gap-3 text-foreground"
        >
          <span
            aria-hidden="true"
            className="h-8 w-8 bg-foreground"
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
          <span className="font-display text-2xl font-extrabold uppercase leading-none tracking-[-0.045em]">
            ASHFALL
          </span>
        </a>

        <nav
          aria-label="Primary navigation"
          className="hidden items-center gap-3 lg:flex"
        >
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground transition-colors duration-300 hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
          <button
            type="button"
            className="font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-muted-foreground transition-colors duration-300 hover:text-foreground"
            aria-label="More navigation options"
          >
            More
          </button>
          <span className="border-l border-border pl-3 font-body text-sm font-medium leading-5 text-muted-foreground">
            PlayStation 5, Xbox Series X|S, and PC.
          </span>
        </nav>

        <div className="flex items-center gap-3">
          <details className="relative lg:hidden">
            <summary className="cursor-pointer list-none border border-border px-4 py-3 font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-foreground transition-colors duration-300 hover:border-muted-foreground">
              Menu
            </summary>
            <div className="absolute right-0 top-[calc(100%+1rem)] w-[18rem] border border-border bg-card p-6 text-foreground">
              <nav aria-label="Mobile navigation" className="space-y-4">
                {navItems.map((item) => (
                  <a
                    key={item.label}
                    href={item.href}
                    className="block font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-foreground"
                  >
                    {item.label}
                  </a>
                ))}
                <button
                  type="button"
                  className="block font-mono text-xs font-semibold uppercase leading-4 tracking-[0.14em] text-foreground"
                >
                  More
                </button>
                <div className="border-t border-border pt-4 font-body text-sm font-medium leading-5 text-muted-foreground">
                  {platforms.map((platform, index) => (
                    <span key={platform}>
                      {platform}
                      {index < platforms.length - 1 ? ", " : "."}
                    </span>
                  ))}
                </div>
              </nav>
            </div>
          </details>

          <motion.a
            href="#preorder"
            initial={{ y: reduceMotion ? 0 : -3 }}
            animate={{ y: 0 }}
            whileHover={{ y: reduceMotion ? 0 : -2 }}
            transition={{
              duration: 0.3,
              ease: [0.06, 0.81, 0, 0.98],
            }}
            className="rounded-sm border border-accent/40 bg-primary px-4 py-3 font-body text-sm font-medium leading-5 text-primary-foreground"
          >
            Pre-order now
          </motion.a>
        </div>
      </div>
    </section>
  );
}
