// The console's lint rules. Each project rule below is one written in
// AGENTS.md (the "Rules" sections) — a rule that a tool can check is checked
// here rather than left to be read. Keep the two in step.
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";

// Panels that must reach the page through lazy-panels.tsx, never directly:
// imported eagerly they put ~40 KB and one unsliceable commit back on /build's
// first load (AGENTS.md › Performance).
const LAZY_PANELS = ["studio-panel", "gate-panel", "build-canvas", "preview-pane"];

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  prettier,

  {
    rules: {
      "no-console": "error",
      // An empty catch is allowed only with a comment saying why (no-empty
      // accepts a block that contains one).
      "no-empty": ["error", { allowEmptyCatch: false }],
      "@typescript-eslint/no-explicit-any": "error",
      "react/no-danger": "error",
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXOpeningElement[name.name='script']",
          message:
            "No <script> in JSX: React never runs a script it renders on the client (AGENTS.md › Modern React).",
        },
        {
          selector: "CallExpression[callee.name='eval'], NewExpression[callee.name='Function']",
          message: "No eval / new Function (AGENTS.md › Security).",
        },
      ],
      "@typescript-eslint/no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "motion",
              message:
                "No animation library on first load — CSS transitions (AGENTS.md › Performance).",
            },
            {
              name: "motion/react",
              message:
                "No animation library on first load — CSS transitions (AGENTS.md › Performance).",
            },
            {
              name: "framer-motion",
              message:
                "No animation library on first load — CSS transitions (AGENTS.md › Performance).",
            },
          ],
          patterns: [
            {
              group: LAZY_PANELS.map((p) => `@/components/${p}`),
              allowTypeImports: true,
              message:
                "Import heavy panels from @/components/lazy-panels (AGENTS.md › Performance).",
            },
          ],
        },
      ],
    },
  },

  // Components render and dispatch; transport lives in src/lib (AGENTS.md › Structure).
  {
    files: ["src/app/**", "src/components/**"],
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Call a function in src/lib/ instead (AGENTS.md › Structure)." },
      ],
    },
  },

  // src/lib never imports UI.
  {
    files: ["src/lib/**"],
    rules: {
      "@typescript-eslint/no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/components/*", "@/app/*"],
              message: "src/lib must not import UI (AGENTS.md › Structure).",
            },
          ],
        },
      ],
    },
  },

  // The panels themselves, and the one module allowed to import them eagerly.
  {
    files: ["src/components/lazy-panels.tsx", ...LAZY_PANELS.map((p) => `src/components/${p}.tsx`)],
    rules: { "@typescript-eslint/no-restricted-imports": "off" },
  },

  // Node scripts and tests may log.
  {
    files: ["scripts/**", "**/*.test.ts", "**/*.test.tsx"],
    rules: { "no-console": "off", "no-restricted-globals": "off" },
  },

  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
