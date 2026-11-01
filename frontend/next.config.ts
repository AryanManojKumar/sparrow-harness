import type { NextConfig } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// The console is a served app, not a static export — it proxies to the
// backend and (later) holds an SSE connection open per run. Unlike
// `scaffold/`, which is pinned to `output: "export"` for generated sites,
// this project needs a live server.
const nextConfig: NextConfig = {
  // The generated sites are exported with trailingSlash, so their pages live
  // at /pricing/ and their relative URLs resolve against that slash. Next's
  // default redirect would strip it on the way through the proxy below.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return {
      // Previews are served through this origin rather than straight from the
      // API, so the preview frame is same-origin with the console: the address
      // bar can follow the page the owner clicked to inside the site.
      beforeFiles: [
        { source: "/projects/:pid/preview", destination: `${API_URL}/projects/:pid/preview/` },
        {
          source: "/projects/:pid/preview/:path*",
          destination: `${API_URL}/projects/:pid/preview/:path*`,
        },
      ],
    };
  },
};

export default nextConfig;
