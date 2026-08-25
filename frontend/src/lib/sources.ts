/**
 * A reference site the run will design against.
 *
 * These come from the user — typed into the reference-site fields, or picked
 * up automatically from any URL in the prompt. They are passed straight to
 * `POST /projects` as `urls` and are what scout extracts and ranks
 * (CLAUDE.md §5, backend/src/sparrow/steps.py: step_sources).
 */
export type Source = {
  id: string;
  title: string;
  domain: string;
  url: string;
  description: string;
};
