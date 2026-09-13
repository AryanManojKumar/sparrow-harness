"use client";

import { motion, useReducedMotion } from "motion/react";

const navigation = [
  {
    title: "Product",
    links: ["Features", "Platforms", "Rendering", "World Streaming"],
  },
  {
    title: "Resources",
    links: ["Technical Docs", "Release Notes", "Documentation", "System Requirements", "API Reference"],
  },
  {
    title: "Company",
    links: ["Studio Licensing", "About Meridian", "Careers", "Contact", "Partners"],
  },
  {
    title: "Support",
    links: ["Support Portal", "License Support", "System Status"],
  },
];

const socialIcons: Record<string, React.ReactNode> = {
  LinkedIn: (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <path d="M6.5 9.5V18M6.5 6.5V6.55M10.5 18V12.8C10.5 10.85 11.7 9.5 13.45 9.5C15.2 9.5 16.5 10.85 16.5 12.8V18M16.5 13.2C16.5 10.9 17.65 9.5 19.35 9.5C21.05 9.5 22 10.85 22 12.8V18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
  YouTube: (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <path d="M21 12C21 15.3 20.65 17.15 19.7 18.1C18.75 19.05 16.9 19.4 12 19.4C7.1 19.4 5.25 19.05 4.3 18.1C3.35 17.15 3 15.3 3 12C3 8.7 3.35 6.85 4.3 5.9C5.25 4.95 7.1 4.6 12 4.6C16.9 4.6 18.75 4.95 19.7 5.9C20.65 6.85 21 8.7 21 12Z" stroke="currentColor" strokeWidth="1.7" />
      <path d="M10 9.25L15 12L10 14.75V9.25Z" fill="currentColor" />
    </svg>
  ),
  X: (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <path d="M5 4L18.5 20M19 4L5.5 20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  Discord: (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <path d="M7.2 6.3C9.9 5.45 14.1 5.45 16.8 6.3M8.4 17.35C10.55 18.2 13.45 18.2 15.6 17.35M6.25 8.1C5.15 10.65 5.1 13.75 6.5 16.4L9 17.15L9.85 16.05M17.75 8.1C18.85 10.65 18.9 13.75 17.5 16.4L15 17.15L14.15 16.05M8.25 11.25V11.3M15.75 11.25V11.3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Twitch: (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <path d="M5.5 4.5H19V14.5L15.5 18H12.5L10.5 20V18H7.5L5.5 16V4.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M10 8.5V12M14.5 8.5V12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
  GitHub: (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <path d="M12 19.25C16.28 19.25 19.75 15.78 19.75 11.5C19.75 7.22 16.28 3.75 12 3.75C7.72 3.75 4.25 7.22 4.25 11.5C4.25 14.92 6.47 17.82 9.55 18.85M14.45 18.85C17.53 17.82 19.75 14.92 19.75 11.5M9.55 18.85V16.5C9.55 15.75 9.05 15.2 8.2 15.2C6.85 15.2 6.6 14.2 6.15 13.85M14.45 18.85V16.5C14.45 15.75 14.95 15.2 15.8 15.2C17.15 15.2 17.4 14.2 17.85 13.85M8.75 8.85C10.6 8.35 13.4 8.35 15.25 8.85M9.1 6.85C8.55 6.15 7.55 5.8 6.7 6.05C6.45 6.9 6.8 7.9 7.5 8.45" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
};

export default function Footer() {
  const reducedMotion = useReducedMotion();
  const rise = reducedMotion ? 0 : 11;

  const arrival = {
    initial: { opacity: 0.27, y: rise },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px", amount: 0.1 },
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] },
  };

  return (
    <section className="relative overflow-hidden bg-muted py-24 md:py-32" aria-label="Footer">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.07] mix-blend-screen bg-[repeating-linear-gradient(0deg,transparent_0,transparent_3px,oklch(0.74_0.018_240)_3px,oklch(0.74_0.018_240)_4px)]"
      />

      <div className="relative mx-auto max-w-[81rem] px-6">
        <motion.div
          {...arrival}
          className="border-t border-border pt-8"
        >
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
              Creator credits · Built for studio teams evaluating production systems
            </p>
            <div className="flex items-center gap-3">
              {["LinkedIn", "YouTube", "X", "Discord", "Twitch", "GitHub"].map((label) => (
                <motion.a
                  key={label}
                  href="#"
                  aria-label={label}
                  title={label}
                  whileHover={reducedMotion ? undefined : { y: -2 }}
                  transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground transition-colors duration-300 hover:border-primary hover:text-primary"
                >
                  {socialIcons[label]}
                </motion.a>
              ))}
            </div>
          </div>
        </motion.div>

        <div className="mt-8 grid gap-8 md:grid-cols-12">
          <motion.div
            {...arrival}
            transition={{ duration: 0.2, delay: 0.06, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
            className="space-y-8 md:col-span-4"
          >
            <div className="space-y-4">
              <a href="#top" aria-label="Meridian home" className="inline-flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="h-9 w-9 shrink-0 bg-foreground"
                  style={{
                    maskImage: "url('/assets/nav-logo.png')",
                    maskPosition: "center",
                    maskRepeat: "no-repeat",
                    maskSize: "contain",
                    WebkitMaskImage: "url('/assets/nav-logo.png')",
                    WebkitMaskPosition: "center",
                    WebkitMaskRepeat: "no-repeat",
                    WebkitMaskSize: "contain",
                  }}
                />
                <span className="font-display text-3xl font-semibold leading-[1] tracking-[-0.035em] text-foreground">
                  Meridian
                </span>
              </a>
              <p className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground">
                Real-time production for PC, PlayStation 5, and <span className="whitespace-nowrap">Xbox Series X|S</span>.
              </p>
            </div>

            <motion.div
              whileHover={reducedMotion ? undefined : { y: -2 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
              className="rounded-lg border border-border bg-card p-5 shadow-sm transition-colors duration-300 hover:border-primary hover:shadow-md"
            >
              <div className="space-y-4">
                <div className="space-y-4">
                  <h2 className="font-display text-xl font-semibold leading-tight tracking-[-0.02em] text-foreground md:text-2xl">
                    Updates for studio teams
                  </h2>
                  <p className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground">
                    Get Meridian product news, technical resources, and release updates for your next production.
                  </p>
                </div>

                <form className="space-y-4">
                  <div className="space-y-4">
                    <label htmlFor="footer-email" className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                      Work email
                    </label>
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <input
                        id="footer-email"
                        type="email"
                        name="email"
                        required
                        className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-3 font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
                      />
                      <button
                        type="submit"
                        className="rounded-lg bg-primary px-5 py-3 font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary-foreground shadow-sm transition-shadow duration-300 hover:shadow-md"
                      >
                        Subscribe
                      </button>
                    </div>
                  </div>
                  <label className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      required
                      className="mt-1 h-4 w-4 rounded-md border-border accent-primary"
                    />
                    <span className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground">
                      I agree to receive Meridian updates.
                    </span>
                  </label>
                  <p className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground">
                    You can unsubscribe at any time. See our Privacy Policy for details.
                  </p>
                </form>
              </div>
            </motion.div>
          </motion.div>

          <motion.nav
            {...arrival}
            transition={{ duration: 0.2, delay: 0.14, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
            aria-label="Footer navigation"
            className="grid gap-8 sm:grid-cols-2 md:col-span-8 md:grid-cols-3"
          >
            <FooterGroup group={navigation[0]} />
            <div className="space-y-8">
              <FooterGroup group={navigation[1]} />
              <FooterGroup group={navigation[3]} />
            </div>
            <FooterGroup group={navigation[2]} />
          </motion.nav>
        </div>

        <motion.div
          {...arrival}
          transition={{ duration: 0.2, delay: 0.19, ease: [0.4, 0, 0.2, 1] as [number, number, number, number] }}
          className="mt-8 flex flex-col justify-between gap-8 border-t border-border pt-8 md:flex-row md:items-end"
        >
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
              © Meridian. All rights reserved.
            </p>
            <div className="flex flex-wrap gap-3">
              {["Privacy Policy", "Terms of Use", "Cookie Settings"].map((link) => (
                <a
                  key={link}
                  href="#"
                  className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground transition-colors hover:text-primary"
                >
                  {link}
                </a>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-accent">
              BUILD TARGETS · PC / PLAYSTATION 5 / <span className="whitespace-nowrap">XBOX SERIES X|S</span>
            </p>
            <a
              href="#top"
              className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary transition-colors hover:text-foreground"
            >
              Back to top ↑
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function FooterGroup({
  group,
}: {
  group: { title: string; links: string[] };
}) {
  return (
    <details className="group border-b border-border pb-4 md:border-0 md:pb-0" open>
      <summary className="flex cursor-pointer list-none items-center justify-between font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-foreground marker:hidden md:pointer-events-none">
        {group.title}
        <span className="text-primary transition-transform group-open:rotate-45 md:hidden">+</span>
      </summary>
      <ul className="mt-4 space-y-4">
        {group.links.map((link) => (
          <li key={link}>
            <a
              href="#"
              className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground transition-colors hover:text-primary"
            >
              {link}
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}
