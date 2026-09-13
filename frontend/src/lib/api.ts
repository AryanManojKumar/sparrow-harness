/**
 * Client for the real backend — see backend/API.md and backend/src/sparrow/api.py.
 *
 * A run is not request/response: it takes minutes and stops twice for a human
 * (three gates minus the brief gate, which this flow always clears up front
 * by supplying a brief at creation time). `advance()` streams SSE for one leg
 * of the run — from wherever it's paused to the next gate, the end, or a
 * failure — and the caller re-invokes it after answering a gate to resume.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Brief = {
  /** The one fact every section must agree on — without it the builders each
   *  invent a name and the nav disagrees with the footer. Extracted by
   *  /interview, so it has to be forwarded here or it is lost. */
  product_name?: string;
  category: string;
  offering: string;
  audience: string;
  tone: string;
  primary_action: string;
  secondary_action?: string | null;
};

export type InterviewResult = {
  brief: Brief;
  constraints: string[];
  assumed: string[];
  confidence: string;
};

async function asJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${what} failed (${res.status}): ${body.slice(0, 300)}`);
  }
  return res.json();
}

export function interview(prompt: string): Promise<InterviewResult> {
  return fetch(`${API_URL}/interview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  }).then((r) => asJson(r, "interview"));
}

export function createProject(input: {
  project_id: string;
  brief: Brief;
  constraints: string[];
  urls: string[];
}): Promise<{ project_id: string; stage: string }> {
  return fetch(`${API_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: input.project_id,
      product_name: input.brief.product_name ?? "",
      category: input.brief.category,
      offering: input.brief.offering,
      audience: input.brief.audience,
      tone: input.brief.tone,
      primary_action: input.brief.primary_action,
      secondary_action: input.brief.secondary_action ?? null,
      constraints: input.constraints,
      urls: input.urls,
    }),
  }).then((r) => asJson(r, "create project"));
}

export type RunEventKind = "started" | "progress" | "blocked" | "awaiting" | "done" | "failed";

export type RunEvent = {
  stage: string;
  kind: RunEventKind;
  message: string;
  cost: number;
  data: Record<string, unknown>;
  spent: number;
};

/**
 * Drives one leg of a run: from wherever it's paused to the next gate, the
 * end, or a failure. POST + a hand-rolled SSE reader, not EventSource —
 * EventSource is GET-only and this endpoint is a POST.
 */
export async function advance(
  projectId: string,
  onEvent: (e: RunEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/projects/${projectId}/advance`, {
    method: "POST",
    signal,
  });
  return readEvents(res, "advance", onEvent);
}

/**
 * Attach to a run that is already advancing — started from another tab, from
 * curl, or from this tab before a reload. Replays everything emitted so far,
 * then follows the live tail. Never starts anything: if nothing is running it
 * ends immediately, and the caller should read `getProject` for where the
 * project is parked.
 */
export async function follow(
  projectId: string,
  onEvent: (e: RunEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/projects/${projectId}/events`, { signal });
  return readEvents(res, "follow", onEvent);
}

async function readEvents(
  res: Response,
  what: string,
  onEvent: (e: RunEvent) => void
): Promise<void> {
  if (!res.ok || !res.body) {
    throw new Error(`${what} failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    const chunks = buf.split("\n\n");
    buf = chunks.pop() ?? "";

    for (const chunk of chunks) {
      if (chunk.includes("event: end")) continue;
      if (chunk.startsWith(":")) continue; // keepalive comment
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice("data: ".length)) as RunEvent);
      } catch {
        // A malformed chunk shouldn't kill the stream — skip it.
      }
    }
  }
}

/**
 * One choice at a gate. At gate 2 these are design directions and carry a
 * `specimen` — a rendered PNG of the direction's actual palette and type.
 * The backend renders those precisely because the prose signature ("a
 * perforated remittance-advice ribbon") is not something a business owner
 * can answer; swatches are. Index -1 is the "none of these" escape hatch,
 * which requires a note saying what to change.
 *
 * At the material gate, options split on `kind`:
 * - "image": asset upload/generate/skip decisions
 * - "fact": invented copy that needs confirmation (ask_id, draft, invented)
 */
/** One answer the gate offers for an asset or a fact. */
export type GateChoice = {
  choice: string;
  label: string;
  detail?: string;
  /** Facts only: "text" means this answer takes a typed value. */
  field?: string;
  /** Uploads only: the human-readable list of formats this slot takes. */
  accepts?: string;
  /** Uploads only: where the file goes. */
  post_file_to?: string;
};

/** Every kind of thing the material gate can ask about. `logo` and `video`
 *  are asset kinds alongside `image`; each carries its own `choices`, and
 *  they differ — a logo can be a wordmark but never generated, a video is
 *  used untouched if uploaded. Render the choices the server sends rather
 *  than assuming three radios; that assumption is what dropped the logo and
 *  video rows on the floor and left the gate impossible to answer. */
export type AssetKind = "image" | "logo" | "video";

export type GateOption = {
  kind?: AssetKind | "fact";
  choice?: string | number;
  label?: string;
  index?: number;
  signature?: string;
  atmosphere?: string;
  type?: string;
  specimen?: string | null;
  // Asset fields
  asset_id?: string;
  brief?: string;
  prominence?: string;
  uploaded?: boolean;
  // Fact question fields
  ask_id?: string;
  section_id?: string;
  slot?: string;
  question?: string;
  draft?: string;
  invented?: string;
  source_example?: string;
  choices?: GateChoice[];
};

/** One row of the asset plan — what the run intends to make or use for a
 *  slot. `decision` is null until the gate is answered. */
export type AssetPlanEntry = {
  id: string;
  section_id: string;
  kind?: AssetKind;
  brief: string;
  prominence: string;
  decision?: "upload" | "generate" | "skip" | "wordmark" | null;
  upload?: string | null;
};

/** The plan, before or after the gate. 404s until the run has one. */
export function getAssetPlan(projectId: string): Promise<AssetPlanEntry[]> {
  return fetch(`${API_URL}/projects/${projectId}/assets`)
    .then((r) => (r.ok ? r.json() : []))
    .catch(() => []);
}

/** Where a produced asset can be fetched from, the moment it exists —
 *  before BUILD has written the export that `/preview/` serves from. */
export function producedFileUrl(projectId: string, path: string): string {
  return `${API_URL}/projects/${projectId}/files/${path}`;
}

/** An asset the run actually produced, as recorded on the blackboard.
 *  `path` is relative to `workspace/public`; see `producedFileUrl`. */
export type BlackboardAsset = {
  id: string;
  section_id: string;
  kind: AssetKind;
  provenance: "generated" | "user_supplied" | string;
  path: string;
  width?: number;
  height?: number;
  brief?: string;
};

export type GateInfo = {
  awaiting: boolean;
  gate?: string;
  question?: string;
  options?: GateOption[];
  artifacts?: string[];
};

/** Absolute URL for a server-relative artifact path the API handed back. */
export function assetUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

export function getGate(projectId: string): Promise<GateInfo> {
  return fetch(`${API_URL}/projects/${projectId}/gate`).then((r) => asJson(r, "gate"));
}

export type Direction = {
  index: number;
  signature: string;
  atmosphere: string;
  type: string;
  revised: string;
};

export function getDirections(projectId: string): Promise<Direction[]> {
  return fetch(`${API_URL}/projects/${projectId}/directions`).then((r) => asJson(r, "directions"));
}

export function answerGate(
  projectId: string,
  payload: {
    choice?: string | number;
    note?: string;
    assets?: Record<string, string>;
    content?: Record<string, string>;
  }
): Promise<{ stage: string; decisions?: Record<string, string>; content_answered?: number }> {
  return fetch(`${API_URL}/projects/${projectId}/gate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => asJson(r, "answer gate"));
}

export function uploadAsset(
  projectId: string,
  assetId: string,
  file: File
): Promise<{ asset_id: string; stored: string; bytes: number }> {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API_URL}/projects/${projectId}/assets/${assetId}`, {
    method: "POST",
    body: formData,
  }).then((r) => asJson(r, "upload asset"));
}

export function previewUrl(projectId: string): string {
  return `${API_URL}/projects/${projectId}/preview/`;
}

/**
 * A still of the built page, for cards and for the workspace's pre-build
 * poster. Cheap and cached server-side — unlike `previewUrl`, which is a
 * whole live site and costs a page load every time it is mounted.
 */
export function thumbUrl(projectId: string): string {
  return `${API_URL}/projects/${projectId}/thumb`;
}

/** One section's capture from the last verify pass. */
export function sectionShotUrl(projectId: string, index: number,
                               device: "desktop" | "mobile" = "desktop"): string {
  const n = String(index).padStart(2, "0");
  return `${API_URL}/projects/${projectId}/shots/sections/${device}-s${n}.png`;
}

/** Filesystem-safe, human-readable project id derived from the prompt. */
export function slugify(text: string): string {
  const base = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  const suffix = Date.now().toString(36).slice(-5);
  return `${base || "project"}-${suffix}`;
}

/* --------------------------------------------------------------- projects */

/**
 * One row of GET /projects.
 *
 * `project_id` is the directory name and the ONLY id that can be navigated
 * to — the blackboard carries a field of the same name that can disagree
 * with it, and reading that one instead is exactly the bug that sent the UI
 * to the wrong project. Never derive the id from anywhere else.
 *
 * A row with `readable: false` predates a schema change and cannot be
 * parsed, but still carries id, timestamp and preview flag, so it renders as
 * a disabled card rather than taking the whole list down.
 */
export type ProjectSummary = {
  project_id: string;
  readable: boolean;
  reason?: string;
  product_name?: string;
  category?: string;
  stage?: string;
  sections?: number;
  built?: number;
  assets?: number;
  has_preview?: boolean;
  /** Whether `thumbUrl` can answer without launching a browser first. */
  thumb_ready?: boolean;
  /** A run is executing on the server right now — follow it, don't offer Resume. */
  running?: boolean;
  updated_at?: number;
};

/** Already sorted newest-first by the API — render in the order given. */
export function listProjects(): Promise<ProjectSummary[]> {
  return fetch(`${API_URL}/projects`).then((r) => asJson(r, "list projects"));
}

/**
 * One section of the page, as `compose` left it.
 *
 * This is the plan the builder works from, and it exists on the blackboard
 * well before any of it is built — which is what lets the workspace show the
 * shape of the page while it is still being made, instead of a spinner.
 */
export type Section = {
  id: string;
  order: number;
  blueprint_id: string;
  component_name?: string;
  /** compose's call, not the builder's — see CLAUDE.md §6. */
  ground?: string;
  width?: string;
  archetype?: string;
  archetype_how?: string;
  /** Why this section looks different from its neighbours. Written for a
   *  human, so it can be shown to one. */
  contrast?: string;
  treatments?: { name?: string; where?: string; how?: string }[];
  /** Exactly one section on the page carries it. */
  carries_signature?: boolean;
  carries_motion?: boolean;
  status?: string;
  attempts?: number;
};

export type ProjectDetail = {
  project_id: string;
  stage: string;
  /** True while a run is executing on the server. The console used to ignore
   *  this and show "Stopped" over a run in progress. */
  advancing?: boolean;
  spent: number;
  awaiting_gate: string | null;
  blackboard: {
    brief?: Brief | null;
    sections?: Section[];
    assets?: BlackboardAsset[];
  };
  log: { stage: string; kind: string; message: string; cost: number }[];
};

/** The page plan alone — cheap enough to re-read whenever a stage lands. */
export function getSections(projectId: string): Promise<Section[]> {
  return getProject(projectId)
    .then((d) => (d.blackboard?.sections ?? []).slice().sort((a, b) => a.order - b.order))
    .catch(() => []);
}

/** What the run has produced so far — populated by the assets stage. */
export function getMadeAssets(projectId: string): Promise<BlackboardAsset[]> {
  return getProject(projectId)
    .then((d) => d.blackboard?.assets ?? [])
    .catch(() => []);
}

export function getProject(projectId: string): Promise<ProjectDetail> {
  return fetch(`${API_URL}/projects/${projectId}`).then((r) => asJson(r, "project"));
}

/** A stage id like "gate:design" means a human is blocking the run. */
export function isWaitingOnHuman(stage?: string): boolean {
  return Boolean(stage?.startsWith("gate:"));
}
