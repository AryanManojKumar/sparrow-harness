/**
 * Mocked stand-in for the real progress signal — `sections[].status` and
 * the `decisions` log on the blackboard (backend/src/sparrow/blackboard).
 * Once the run endpoint exists this becomes an SSE subscription keyed by
 * blackboard version instead of a client-side timer.
 */

export type SectionStatus = "pending" | "building" | "done";

export type SectionState = {
  name: string;
  status: SectionStatus;
};

export const MOCK_SECTIONS = ["Hero", "Features", "Pricing", "Testimonials", "Footer"];

const STEP_MS = 900;

export function initialSections(): SectionState[] {
  return MOCK_SECTIONS.map((name) => ({ name, status: "pending" }));
}

/**
 * Drives a mocked build: each section goes pending -> building -> done in
 * sequence. Calls `onUpdate` after every state change and `onComplete` once
 * the last section finishes. Returns a cleanup function that cancels any
 * pending timers.
 */
export function runMockBuild(
  onUpdate: (sections: SectionState[]) => void,
  onComplete: () => void
): () => void {
  const sections = initialSections();
  const timers: ReturnType<typeof setTimeout>[] = [];

  MOCK_SECTIONS.forEach((_, i) => {
    timers.push(
      setTimeout(() => {
        sections[i] = { ...sections[i], status: "building" };
        onUpdate([...sections]);
      }, i * STEP_MS * 2)
    );
    timers.push(
      setTimeout(() => {
        sections[i] = { ...sections[i], status: "done" };
        onUpdate([...sections]);
        if (i === MOCK_SECTIONS.length - 1) onComplete();
      }, i * STEP_MS * 2 + STEP_MS)
    );
  });

  return () => timers.forEach(clearTimeout);
}
