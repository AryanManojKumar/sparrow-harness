import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

// Unit tests for logic, in Node. Component tests (jsdom + Testing Library) are
// added with the first one that needs them — not before (AGENTS.md › Testing).
export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: { include: ["src/**/*.test.{ts,tsx}"], environment: "node" },
});
