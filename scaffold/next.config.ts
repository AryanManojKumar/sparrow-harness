import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export — SSG output. SEO is non-negotiable for business sites.
  output: "export",

  // Required under `output: export` — no server-side image optimizer at runtime.
  // Assets are pre-sized by `curator` into variants before they reach the builder.
  images: { unoptimized: true },

  // Emit /about/index.html rather than /about.html, so any static host serves
  // clean URLs without rewrite rules.
  trailingSlash: true,
};

export default nextConfig;
