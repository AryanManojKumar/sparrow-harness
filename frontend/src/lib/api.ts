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
  if (!res.ok || !res.body) {
    throw new Error(`advance failed (${res.status})`);
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

export type GateInfo = {
  awaiting: boolean;
  gate?: string;
  question?: string;
  options?: { choice?: string | number; label?: string; [k: string]: unknown }[];
  artifacts?: string[];
};

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
  choice: string | number,
  note?: string
): Promise<{ stage: string }> {
  return fetch(`${API_URL}/projects/${projectId}/gate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ choice, note }),
  }).then((r) => asJson(r, "answer gate"));
}

export function previewUrl(projectId: string): string {
  return `${API_URL}/projects/${projectId}/preview/`;
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
