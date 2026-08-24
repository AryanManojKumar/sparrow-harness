"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  advance,
  answerGate,
  createProject,
  getDirections,
  getGate,
  interview,
  previewUrl,
  type Direction,
  type GateInfo,
  type RunEvent,
} from "@/lib/api";
import type { Source } from "@/lib/sources";
import { BuildFeed } from "@/components/build-feed";
import { PreviewPane } from "@/components/preview-pane";

type StoredPayload = { prompt: string; urls: string[]; source: Source | null };

type Phase = "loading" | "interview" | "create" | "run" | "gate" | "done" | "error";

export function BuildWorkspace() {
  const params = useSearchParams();
  const id = params.get("id");

  const [phase, setPhase] = useState<Phase>("loading");
  const [stored, setStored] = useState<StoredPayload | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [spent, setSpent] = useState(0);
  const [gate, setGate] = useState<GateInfo | null>(null);
  const [directions, setDirections] = useState<Direction[] | null>(null);
  const [previewReady, setPreviewReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const startedRef = useRef(false);

  // One leg of the run: from wherever it's paused to the next gate, the end,
  // or a failure. Re-entered after every gate answer, so the same function
  // both kicks the run off and resumes it.
  async function runLeg(projectId: string) {
    setPhase("run");
    let last: RunEvent | null = null;
    try {
      await advance(projectId, (evt) => {
        last = evt;
        setEvents((prev) => [...prev, evt]);
        setSpent(evt.spent);
        // The static export exists as soon as BUILD finishes — well before
        // the VERIFY/GATE_PREVIEW that follows it.
        if (evt.stage === "build" && evt.kind === "done") setPreviewReady(true);
      });
    } catch (e) {
      setPhase("error");
      setErrorMessage(e instanceof Error ? e.message : String(e));
      return;
    }

    if (!last) {
      setPhase("error");
      setErrorMessage("The run ended without reporting anything.");
      return;
    }
    const finalEvent: RunEvent = last;

    if (finalEvent.kind === "failed") {
      setPhase("error");
      setErrorMessage(finalEvent.message);
      return;
    }
    if (finalEvent.kind === "awaiting") {
      const g = await getGate(projectId);
      setGate(g);
      if (g.gate === "gate:design") {
        setDirections(await getDirections(projectId));
      }
      setPhase("gate");
      return;
    }
    setPreviewReady(true);
    setPhase("done");
  }

  async function answerAndContinue(choice: string | number, note?: string) {
    if (!id) return;
    setGate(null);
    setDirections(null);
    try {
      await answerGate(id, choice, note);
    } catch (e) {
      setPhase("error");
      setErrorMessage(e instanceof Error ? e.message : String(e));
      return;
    }
    await runLeg(id);
  }

  useEffect(() => {
    if (!id) {
      setPhase("error");
      setErrorMessage("No project to run — start from the home screen.");
      return;
    }
    const raw = sessionStorage.getItem(`sparrow:${id}`);
    if (!raw) {
      setPhase("error");
      setErrorMessage("This project's details expired — start again from the home screen.");
      return;
    }
    const payload = JSON.parse(raw) as StoredPayload;
    setStored(payload);

    if (startedRef.current) return;
    startedRef.current = true;

    (async () => {
      try {
        setPhase("interview");
        const iv = await interview(payload.prompt);
        setPhase("create");
        await createProject({
          project_id: id,
          brief: iv.brief,
          constraints: iv.constraints,
          urls: payload.urls,
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        // A reload or a second tab on the same project id hits this — the
        // project already exists, which isn't a failure, it's a resume.
        // Check whether the run is already halted at a gate before doing
        // anything else, rather than assuming it needs a fresh leg.
        if (!/\b409\b|already exists/i.test(msg)) {
          setPhase("error");
          setErrorMessage(msg);
          return;
        }
        try {
          const g = await getGate(id);
          if (g.awaiting) {
            setGate(g);
            if (g.gate === "gate:design") setDirections(await getDirections(id));
            setPhase("gate");
            return;
          }
        } catch (e2) {
          setPhase("error");
          setErrorMessage(e2 instanceof Error ? e2.message : String(e2));
          return;
        }
      }
      await runLeg(id);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div className="grid h-screen grid-cols-1 md:grid-cols-[380px_1fr]">
      <div className="border-r border-border bg-card/30">
        <BuildFeed
          prompt={stored?.prompt ?? "…"}
          urls={stored?.urls ?? []}
          source={stored?.source ?? null}
          phase={phase}
          events={events}
          spent={spent}
          gate={gate}
          directions={directions}
          errorMessage={errorMessage}
          onAnswerGate={answerAndContinue}
        />
      </div>
      <PreviewPane
        ready={previewReady}
        src={id && previewReady ? previewUrl(id) : undefined}
        waitingLabel={
          phase === "interview"
            ? "Drafting the brief…"
            : phase === "create"
              ? "Creating the project…"
              : phase === "error"
                ? "Run stopped — see the feed"
                : "Building preview…"
        }
      />
    </div>
  );
}
