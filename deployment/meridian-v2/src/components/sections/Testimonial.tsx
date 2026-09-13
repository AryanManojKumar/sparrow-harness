"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";

const testimonials = [
  {
    project: "Starfall",
    studio: "Arclight Studios",
    publisher: "Helios Interactive",
    quote:
      "“Meridian let us bring the world together without treating performance as an afterthought.”",
    speaker: "Elena Maren",
    role: "Technical Director, Arclight Studios",
    image: "/assets/testimonial-1.png",
    position: "50% center",
  },
  {
    project: "Ashes of the Crown",
    studio: "Iron Vale Games",
    publisher: "Crownforge Publishing",
    quote:
      "“We could take bigger scenes from concept to console and PC with confidence.”",
    speaker: "David Okafor",
    role: "Engine Director, Iron Vale Games",
    image: "/assets/testimonial-2.png",
    position: "24% center",
  },
  {
    project: "Blackwater Protocol",
    studio: "Northline Interactive",
    publisher: "Atlas Entertainment",
    quote:
      "“The rendering stack gave technical art and engineering a shared language from the start.”",
    speaker: "Maya Chen",
    role: "Studio Head, Northline Interactive",
    image: "/assets/testimonial-3.png",
    position: "76% center",
  },
];

export default function Testimonial() {
  const reduceMotion = useReducedMotion();
  const rise = reduceMotion ? 0 : 11;
  const cardRise = reduceMotion ? 0 : 2;

  return (
    <section className="bg-background py-24 md:py-32">
      <div className="mx-auto max-w-[1253px] px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <motion.header
            className="space-y-4 lg:col-span-4"
            initial={{ opacity: 0.27, y: rise }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px", amount: 0.1 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          >
            <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
              From the teams building worlds
            </p>
            <h2 className="font-display text-3xl font-semibold leading-[1] tracking-[-0.035em] text-foreground md:text-5xl">
              For worlds built to ship on console and PC.
            </h2>
          </motion.header>

          <div className="grid grid-cols-1 gap-8 md:grid-cols-8 lg:col-span-8">
            {testimonials.map((testimonial, index) => {
              const isLead = index === 0;

              return (
                <motion.article
                  key={testimonial.project}
                  className={`group rounded-lg border border-border bg-card shadow-sm transition-shadow duration-300 hover:border-primary hover:shadow-md ${
                    isLead ? "md:col-span-4" : "md:col-span-2"
                  }`}
                  initial={{ opacity: 0.27, y: rise }}
                  whileInView={{ opacity: 1, y: 0 }}
                  whileHover={{ y: -cardRise }}
                  viewport={{ once: true, margin: "-80px", amount: 0.1 }}
                  transition={{
                    duration: 0.3,
                    delay: 0.14 + index * 0.05,
                    ease: [0.4, 0, 0.2, 1],
                  }}
                >
                  <div className="space-y-4 p-6">
                    <div className="relative aspect-[3/2] overflow-hidden rounded-lg ring-1 ring-inset ring-border/70">
                      <Image
                        src={testimonial.image}
                        alt={`${testimonial.project} in-engine project capture`}
                        fill
                        unoptimized
                        sizes={
                          isLead
                            ? "(min-width: 1024px) 28vw, (min-width: 768px) 48vw, 100vw"
                            : "(min-width: 1024px) 14vw, (min-width: 768px) 24vw, 100vw"
                        }
                        className="object-cover"
                        style={{ objectPosition: testimonial.position }}
                      />
                      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,oklch(0.12_0.012_250_/_0.72)_100%)]" />
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-4">
                        <h3 className="font-display text-xl font-semibold leading-tight tracking-[-0.02em] text-foreground md:text-2xl">
                          {testimonial.project}
                        </h3>
                        <div className="space-y-4">
                          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                            {testimonial.studio}
                          </p>
                          <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-muted-foreground">
                            {testimonial.publisher}
                          </p>
                        </div>
                      </div>

                      <blockquote className="font-body text-base font-normal leading-7 tracking-[-0.01em] text-foreground md:text-lg">
                        {testimonial.quote}
                      </blockquote>

                      <div className="border-t border-border pt-4">
                        <p className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-foreground">
                          {testimonial.speaker}
                        </p>
                        <p className="font-body text-sm font-medium leading-6 tracking-[-0.005em] text-muted-foreground">
                          {testimonial.role}
                        </p>
                      </div>

                      {isLead && (
                        <p className="font-mono text-xs font-medium uppercase leading-5 tracking-[0.14em] text-primary">
                          PC · PlayStation 5 · Xbox Series X|S
                        </p>
                      )}
                    </div>
                  </div>
                </motion.article>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
