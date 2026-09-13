"use client";

import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

const navigation = [
  { label: "Engine", href: "/engine" },
  { label: "Technology", href: "/technology" },
  { label: "Open Worlds", href: "/open-worlds" },
  { label: "Rendering", href: "/rendering" },
  { label: "Technical Docs", href: "/docs" },
  { label: "Resources", href: "/resources" },
  { label: "Studio Licensing", href: "/studio-licensing" },
];

export default function Nav() {
  const [menuOpen, setMenuOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  const entrance = {
    initial: { opacity: 0.9, y: reduceMotion ? 0 : -5 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] as const },
  };

  return (
    <section className="relative z-50 border-b border-border bg-background">
      <motion.nav
        {...entrance}
        aria-label="Primary navigation"
        className="relative mx-auto flex w-[calc(100%-3rem)] max-w-[1310px] items-center justify-between py-4"
      >
        <Link
          href="#top"
          className="group flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
        >
          <span
            aria-hidden="true"
            className="h-7 w-7 shrink-0 bg-primary transition-transform duration-300 group-hover:-translate-y-px"
            style={{
              WebkitMaskImage:
                "url('/assets/nav-logo.png')",
              WebkitMaskPosition: "center",
              WebkitMaskRepeat: "no-repeat",
              WebkitMaskSize: "contain",
              maskImage:
                "url('/assets/nav-logo.png')",
              maskPosition: "center",
              maskRepeat: "no-repeat",
              maskSize: "contain",
            }}
          />
          <span className="font-display text-xl font-semibold leading-tight tracking-[-0.02em] text-foreground">
            Meridian
          </span>
        </Link>

        <div className="hidden items-center gap-3 xl:flex">
          {navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-1 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground transition-colors duration-300 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
            >
              {item.label}
            </Link>
          ))}
        </div>

        <Link
          href="/studio-licensing"
          className="hidden rounded-lg bg-primary px-4 py-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary-foreground shadow-sm transition-all duration-300 hover:-translate-y-px hover:shadow-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary xl:inline-flex"
        >
          Request a License
        </Link>

        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls="meridian-mobile-navigation"
          onClick={() => setMenuOpen((open) => !open)}
          className="rounded-md border border-border px-3 py-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground transition-colors duration-300 hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary xl:hidden"
        >
          Menu
        </button>
      </motion.nav>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            id="meridian-mobile-navigation"
            initial={{
              opacity: 0.9,
              y: reduceMotion ? 0 : -8,
            }}
            animate={{ opacity: 1, y: 0 }}
            exit={{
              opacity: 0,
              y: reduceMotion ? 0 : -8,
            }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="absolute left-0 right-0 top-full border-b border-border bg-card shadow-md xl:hidden"
          >
            <div className="mx-auto w-[calc(100%-3rem)] max-w-[1310px] py-4">
              <div className="space-y-4">
                {navigation.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className="block font-body text-base font-normal leading-7 tracking-[-0.01em] text-muted-foreground transition-colors duration-300 hover:text-foreground focus-visible:outline-none focus-visible:text-primary"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
              <Link
                href="/studio-licensing"
                onClick={() => setMenuOpen(false)}
                className="mt-8 inline-flex rounded-lg bg-primary px-4 py-2 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary-foreground shadow-sm transition-all duration-300 hover:-translate-y-px hover:shadow-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              >
                Request a License
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
