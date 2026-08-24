import type { NextConfig } from "next";

// The console is a served app, not a static export — it proxies to the
// backend and (later) holds an SSE connection open per run. Unlike
// `scaffold/`, which is pinned to `output: "export"` for generated sites,
// this project needs a live server.
const nextConfig: NextConfig = {};

export default nextConfig;
