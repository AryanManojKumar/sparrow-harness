import { describe, expect, it } from "vitest";

import { slugify } from "@/lib/api";

// A project id becomes a directory on the backend, which validates it against
// ^[a-z0-9][a-z0-9_-]{0,63}$ (workshop/store.py) — every id slugify makes must pass.
const BACKEND_PID = /^[a-z0-9][a-z0-9_-]{0,63}$/;

describe("slugify", () => {
  it("slugify_prompt_lowercaseHyphenatedWithSuffix", () => {
    const id = slugify("Website for Tabby Hours, a cat café in Pune");
    expect(id).toMatch(/^website-for-tabby-hours-a-cat-caf-in-pun-[a-z0-9]{1,5}$/);
  });

  it("slugify_anyInput_passesBackendIdRule", () => {
    for (const text of ["Tabby Hours", "!!!", "", "   ", "日本語のサイト", "a".repeat(200)]) {
      expect(slugify(text)).toMatch(BACKEND_PID);
    }
  });

  it("slugify_onlySymbols_fallsBackToProject", () => {
    expect(slugify("!!!")).toMatch(/^project-/);
  });
});
