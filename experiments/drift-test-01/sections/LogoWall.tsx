"use client";

import { motion } from "motion/react";

type Wordmark = {
  name: string;
  className: string;
};

const wordmarks: Wordmark[] = [
  { name: "Kestrel", className: "text-lg md:text-xl font-semibold tracking-tight" },
  { name: "Arbor Pay", className: "text-lg md:text-xl font-normal tracking-tight" },
  { name: "Halden", className: "text-xs md:text-sm font-medium uppercase tracking-widest" },
  { name: "Northwind", className: "text-lg md:text-xl font-medium tracking-tight" },
  { name: "Sable", className: "text-lg md:text-xl font-semibold tracking-tight" },
  { name: "Verity Rail", className: "text-xs md:text-sm font-medium uppercase tracking-widest" },
];

export default function LogoWall() {
  return (
    <section className="bg-background py-12 md:py-16">
      <div className="mx-auto max-w-6xl px-6">
        <div className="space-y-8">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="text-center text-sm leading-normal text-muted-foreground"
          >
            Holding SOC 2 Type II with evidence collected continuously
          </motion.p>

          <ul className="grid grid-cols-3 items-center justify-items-center gap-8 md:grid-cols-6">
            {wordmarks.map((mark, i) => (
              <motion.li
                key={mark.name}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.6 }}
                transition={{
                  duration: 0.4,
                  ease: "easeOut",
                  delay: 0.06 * (i + 1),
                }}
                className="flex w-full items-center justify-center"
              >
                <span
                  className={`whitespace-nowrap text-muted-foreground transition-colors duration-150 hover:text-foreground ${mark.className}`}
                >
                  {mark.name}
                </span>
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
