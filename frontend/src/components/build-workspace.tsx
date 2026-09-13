"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  advance,
  answerGate,
  follow,
  createProject,
  getAssetPlan,
  getDirections,
  getGate,
  getMadeAssets,
  getProject,
  getSections,
  interview,
  previewUrl,
  type AssetPlanEntry,
  type BlackboardAsset,
  type Direction,
  type GateInfo,
  type RunEvent,
  type Section,
} from "@/lib/api";
import { BuildCanvas } from "@/components/build-canvas";
import { BuildFeed } from "@/components/build-feed";
import { PreviewPane } from "@/components/preview-pane";
import { GatePanel } from "@/components/gate-panel";

type StoredPayload = { prompt: string; urls: string[] };

// "paused" is a resumed project that is NOT blocked on a human: the run
// simply stopped part-way. It must never advance on its own — advancing is
// billable, so it takes an explicit click.
type Phase =
  | "loading"
  | "interview"
  | "create"
  | "run"
  | "gate"
  | "paused"
  | "done"
  | "error";

export function BuildWorkspace() {
  const params = useSearchParams();
  const id = params.get("id");
  // Set by a card on the home screen: the project already exists, so the
  // interview and creation steps must be skipped entirely.
  const isResume = params.get("resume") === "1";
  // The card already knows whether an export exists; trusting it avoids a
  // "Building preview…" placeholder over a site that is already built.
  const resumeHasPreview = params.get("preview") === "1";

  const [phase, setPhase] = useState<Phase>("loading");
  const [stored, setStored] = useState<StoredPayload | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [spent, setSpent] = useState(0);
  const [gate, setGate] = useState<GateInfo | null>(null);
  const [directions, setDirections] = useState<Direction[] | null>(null);
  const [previewReady, setPreviewReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [stoppedStage, setStoppedStage] = useState<string | null>(null);
  // The page plan, for the live canvas. Written by `compose`, so it does not
  // exist for the first half of a run and is fetched the moment it does.
  const [sections, setSections] = useState<Section[]>([]);
  // The API's reason for refusing the last gate answer, if any.
  const [gateError, setGateError] = useState<string | null>(null);
  // What the run intends to make (the plan, fixed at the asset gate) and what
  // it has actually made (the blackboard's assets, written by the stage).
  // Two lists because they are true at different times: the plan is known
  // minutes before the first file exists.
  const [assetPlan, setAssetPlan] = useState<AssetPlanEntry[]>([]);
  const [madeAssets, setMadeAssets] = useState<BlackboardAsset[]>([]);
  const startedRef = useRef(false);

  // One leg of the run: from wherever it's paused to the next gate, the end,
  // or a failure. Re-entered after every gate answer, so the same function
  // both kicks the run off and resumes it.
  //
  // `attach` follows a leg that is already in flight instead of starting one
  // — a run begun from curl, another tab, or this tab before a reload. Same
  // events, same ending; the only difference is which request opens the
  // stream. Everything after the stream closes is identical, which is the
  // point: a followed run reaches its gate on this screen exactly as one
  // started here does.
  async function runLeg(projectId: string, attach = false) {
    setPhase("run");
    let last: RunEvent | null = null;
    const drive = attach ? follow : advance;
    try {
      await drive(projectId, (evt) => {
        last = evt;
        setEvents((prev) => [...prev, evt]);
        setSpent(evt.spent);
        // `compose` is what writes the sections, so this is the first moment
        // there is a page plan to draw. Fetched once, here, rather than
        // polled — the canvas needs it for the rest of the run.
        if (evt.stage === "compose" && evt.kind === "done") {
          getSections(projectId).then(setSections);
        }
        // The plan is fixed the moment the assets stage starts (the gate
        // before it is what wrote the decisions), and the blackboard's
        // asset list is complete when the stage ends. Read each once, at the
        // moment it becomes true; `AssetTray` animates the gap between them
        // off the events themselves.
        if (evt.stage === "assets" && evt.kind === "started") {
          getAssetPlan(projectId).then(setAssetPlan);
        }
        // Every assets-stage event, not only the last one: the stage
        // checkpoints the blackboard after each asset, so each "{id}
        // generated" is a real file with a real path already recorded. One
        // small GET per asset is what lets the picture appear in the tray
        // the moment it exists, rather than when the whole batch is done.
        if (evt.stage === "assets") {
          getMadeAssets(projectId).then(setMadeAssets);
        }
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
      if (attach) {
        // /events ended at once: the run finished between our GET /projects
        // and this call. Not an error — read where it landed instead.
        const g = await getGate(projectId);
        if (g.awaiting) {
          setGate(g);
          if (g.gate === "gate:design") setDirections(await getDirections(projectId));
          setPhase("gate");
        } else {
          setStoppedStage((await getProject(projectId)).stage ?? null);
          setPhase("paused");
        }
        return;
      }
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

  async function answerAndContinue(payload: {
    choice?: string | number;
    note?: string;
    assets?: Record<string, string>;
    content?: Record<string, string>;
  }) {
    if (!id) return;
    setGateError(null);
    try {
      await answerGate(id, payload);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // A 400 is the API refusing THIS answer — the gate is still open and
      // the user can answer it differently. This used to clear the gate
      // before asking and then drop into the error phase, so a refusal
      // left a dead screen with "answer gate failed (400)" and no way back
      // but a reload. Keep the gate up, show the reason on it.
      if (/\b400\b/.test(msg)) {
        setGateError(msg.replace(/^answer gate failed \(400\):\s*/, ""));
        return;
      }
      setPhase("error");
      setErrorMessage(msg);
      return;
    }
    setGate(null);
    setDirections(null);
    // Answering the asset gate is what writes the decisions, so this is the
    // first moment the plan is worth drawing — before the stage even starts.
    if (gate?.gate === "gate:assets") getAssetPlan(id).then(setAssetPlan);
    await runLeg(id);
  }

  useEffect(() => {
    if (!id) {
      setPhase("error");
      setErrorMessage("No project to run — start from the home screen.");
      return;
    }
    const raw = sessionStorage.getItem(`sparrow:${id}`);
    if (!raw && !isResume) {
      setPhase("error");
      setErrorMessage("This project's details expired — start again from the home screen.");
      return;
    }
    const payload = raw ? (JSON.parse(raw) as StoredPayload) : null;
    if (payload) setStored(payload);

    if (startedRef.current) return;
    startedRef.current = true;

    // Resuming an existing project: read where it actually got to and either
    // show the gate it is blocked on or push it along. Nothing is created.
    if (isResume) {
      (async () => {
        try {
          const detail = await getProject(id);
          setSpent(detail.spent ?? 0);
          // A resumed project is usually past compose, so the plan is
          // already on the blackboard — draw it immediately rather than
          // waiting for an event that will not come again.
          setSections(
            (detail.blackboard?.sections ?? []).slice().sort((a, b) => a.order - b.order)
          );
          setMadeAssets(detail.blackboard?.assets ?? []);
          getAssetPlan(id).then(setAssetPlan);
          if (resumeHasPreview) setPreviewReady(true);
          setStoppedStage(detail.stage ?? null);
          if (!payload) {
            const b = detail.blackboard?.brief;
            setStored({
              prompt: b?.product_name?.trim() || b?.offering || id,
              urls: [],
            });
          }
          // Executing right now, on the server. Follow it — this costs
          // nothing and is the whole difference between a live console and
          // one that says "Stopped at sources" over a run extracting
          // sources. Checked BEFORE the gate: a run cannot be at a gate and
          // advancing at once, and this is the state the gate check misses.
          if (detail.advancing) {
            await runLeg(id, true);
            return;
          }
          const g = await getGate(id);
          if (g.awaiting) {
            setGate(g);
            if (g.gate === "gate:design") {
              setDirections(await getDirections(id).catch(() => null));
            }
            setPhase("gate");
            return;
          }
          // Not blocked on anyone — the run just stopped. Opening a project
          // must not restart it: /advance costs real model calls, and doing
          // that as a side effect of a click is how spend happens unasked.
          setPhase("paused");
        } catch (e) {
          setPhase("error");
          setErrorMessage(e instanceof Error ? e.message : String(e));
        }
      })();
      return;
    }

    // Unreachable — the guard above returns when there is no payload and this
    // is not a resume — but it is what proves `payload` non-null from here on.
    if (!payload) return;

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

  // Before anything is built the preview pane has nothing to show, so the
  // open gate takes it — three palettes are judged side by side, not stacked
  // in a 380px column. Once a build exists the preview reclaims the space and
  // the remaining gate (approve / revise) drops back into the sidebar.
  const gateOpen = phase === "gate" && Boolean(gate?.awaiting);
  const gateInMainPane = gateOpen && !previewReady;

  // The stage the run is actually in, as opposed to `phase`, which is the
  // workspace's own state machine. Taken from the last event rather than
  // tracked separately, so it cannot drift from what the feed is showing.
  const liveStage = events.length ? events[events.length - 1].stage : "";
  const liveMessage = events.length ? events[events.length - 1].message : "";

  // While a run is moving and there is nothing built yet, the main pane
  // shows the page being assembled instead of a placeholder. Once an export
  // exists the preview takes it back — a real page beats a drawing of one.
  const showCanvas = phase === "run" && !previewReady;

  const STAGE_HEADLINE: Record<string, string> = {
    brief: "Reading the brief",
    sources: "Studying your reference sites",
    design: "Choosing a direction",
    compose: "Laying out the page",
    content: "Writing the copy",
    assets: "Preparing the imagery",
    build: "Building the sections",
    verify: "Checking the built page",
  };

  return (
    <div className="grid h-screen grid-cols-1 md:grid-cols-[380px_1fr]">
      <div className="border-r border-border bg-card/30 overflow-hidden">
        <BuildFeed
          prompt={stored?.prompt ?? "…"}
          urls={stored?.urls ?? []}
          phase={phase}
          events={events}
          spent={spent}
          gate={gate}
          directions={directions}
          errorMessage={errorMessage}
          showGateInline={!gateInMainPane}
          projectId={id || ""}
          stoppedStage={stoppedStage}
          gateError={gateError}
          assetPlan={assetPlan}
          madeAssets={madeAssets}
          previewReady={previewReady}
          onResume={() => id && runLeg(id)}
          onAnswerGate={answerAndContinue}
        />
      </div>

      {gateInMainPane && gate ? (
        <div className="overflow-y-auto px-6 py-8">
          <GatePanel
            gate={gate}
            directions={directions}
            layout="wide"
            projectId={id || ""}
            serverError={gateError}
            onAnswerGate={answerAndContinue}
          />
        </div>
      ) : showCanvas ? (
        <BuildCanvas
          sections={sections}
          events={events}
          stage={liveStage}
          headline={STAGE_HEADLINE[liveStage] ?? "Building your site"}
          detail={liveMessage}
          assetPlan={assetPlan}
          madeAssets={madeAssets}
          projectId={id || ""}
        />
      ) : (
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
      )}
    </div>
  );
}
