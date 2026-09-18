"use client";

import { useState } from "react";

import { Film, Image as ImageIcon, Sparkles, Stamp, Upload } from "lucide-react";

import {
  assetUrl,
  uploadAsset,
  type AssetKind,
  type Direction,
  type GateInfo,
  type GateOption,
  type GateAnswer,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** What the file picker accepts, by asset kind. The server says the same
 *  thing in prose (`accepts`); this is the machine-readable version, and it
 *  is what stops an SVG being offered for a screenshot or an MP4 for a logo. */
const ACCEPT: Record<AssetKind, string> = {
  image: "image/png,image/jpeg,image/webp",
  logo: "image/png,image/jpeg,image/webp,image/svg+xml",
  video: "video/mp4,video/webm,video/quicktime",
  portrait: "image/png,image/jpeg,image/webp",
};

const KIND_LABEL: Record<AssetKind, string> = {
  logo: "Your logo",
  image: "Images for this page",
  video: "Video",
  portrait: "Your photo",
};

const KIND_ICON: Record<AssetKind, React.ReactNode> = {
  logo: <Stamp className="size-3.5" />,
  image: <ImageIcon className="size-3.5" />,
  video: <Film className="size-3.5" />,
  portrait: <ImageIcon className="size-3.5" />,
};

/** The one-line meaning of a choice, so a user can tell at a glance what
 *  will happen to the site — not only what the radio is called. */
function outcomeOf(choice: string, kind: AssetKind): { icon: React.ReactNode; text: string } {
  switch (choice) {
    case "upload":
      return { icon: <Upload className="size-3" />, text: "your file will be used" };
    case "generate":
      return {
        icon: <Sparkles className="size-3" />,
        text: kind === "video" ? "a video will be generated" : "an image will be generated",
      };
    case "wordmark":
      return { icon: <Stamp className="size-3" />, text: "your name, set in type" };
    default:
      return { icon: null, text: "nothing will be placed here" };
  }
}

/**
 * What the run is waiting on a human to decide.
 *
 * Renders in two places. Until something is built there is no preview to
 * show, so the design gate takes the main pane — the specimens are the
 * decision, and judging three palettes side by side in a 380px column is
 * strictly worse than judging them across the full width. Once a build
 * exists the preview owns that space and the remaining gate is two buttons,
 * which sit fine in the sidebar.
 */
export function GatePanel({
  gate,
  directions,
  layout,
  projectId,
  serverError,
  onAnswerGate,
}: {
  gate: GateInfo;
  directions: Direction[] | null;
  layout: "wide" | "compact";
  projectId: string;
  /** The API's reason for refusing the last answer, shown here so the gate
   *  stays open and answerable instead of collapsing into an error state. */
  serverError?: string | null;
  onAnswerGate: (payload: GateAnswer) => void;
}) {
  const [note, setNote] = useState("");
  const [productName, setProductName] = useState("");
  const [contentAnswers, setContentAnswers] = useState<Record<string, string>>({});
  const [assetDecisions, setAssetDecisions] = useState<Record<string, string>>({});
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, File>>({});
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const wide = layout === "wide";

  // Handler to upload files first, then submit gate
  const handleMaterialGateSubmit = async () => {
    setUploadError(null);
    setUploading(true);
    
    try {
      // Upload any files for assets marked as "upload"
      for (const [assetId, decision] of Object.entries(assetDecisions)) {
        if (decision === "upload") {
          const file = uploadedFiles[assetId];
          if (!file) {
            throw new Error(`${assetId}: chose upload but no file selected`);
          }
          await uploadAsset(projectId, assetId, file);
        }
      }
      
      // All uploads succeeded, now answer the gate
      onAnswerGate({
        assets: assetDecisions,
        content: contentAnswers,
      });
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  };

  // Gate options carry the specimens and the "none of these" escape hatch;
  // GET /directions does not, so prefer options and fall back only if the
  // gate somehow arrived without them.
  const options: GateOption[] = gate.options?.length
    ? gate.options
    : (directions ?? []).map((d) => ({
        index: d.index,
        signature: d.signature,
        atmosphere: d.atmosphere,
        type: d.type,
        specimen: null,
      }));

  const sourcesSpecimen =
    gate.artifacts?.find((a) => a.includes("sources.png")) ?? null;
  const isBriefGate = gate.gate === "gate:brief";
  const isDesignGate = gate.gate === "gate:design";
  const isMaterialGate = gate.gate === "gate:assets";
  // The brief gate's one option, if the server sent it — carries the `why`.
  const nameOption = isBriefGate ? options.find((o) => o.kind === "product_name") : undefined;
  const nameOk = productName.trim().length > 0;

  // Split material gate options into assets and facts. ASSETS, not images:
  // the gate also carries the logo and any video slot, each with its own
  // choices, and a filter that only kept `image` dropped those two rows —
  // the user could never answer them, and the API (correctly) refused the
  // incomplete plan with a 400 that named the logo.
  const assetOptions = options.filter((o) => o.kind !== "fact");
  const factOptions = options.filter((o) => o.kind === "fact");
  const assetKind = (o: GateOption): AssetKind =>
    o.kind === "logo" || o.kind === "video" || o.kind === "portrait" ? o.kind : "image";
  // Logo first — every generated surface is branded from it — then images,
  // then video, which is the same order the assets stage produces them in.
  const KIND_ORDER: AssetKind[] = ["logo", "portrait", "image", "video"];
  const grouped = KIND_ORDER.map((k) => ({
    kind: k,
    items: assetOptions.filter((o) => assetKind(o) === k),
  })).filter((g) => g.items.length > 0);
  const decidedCount = assetOptions.filter(
    (o) => assetDecisions[o.asset_id ?? String(o.choice)]
  ).length;
  const allDecided = decidedCount === assetOptions.length;

  // Initialize content answers with draft values
  if (factOptions.length > 0 && Object.keys(contentAnswers).length === 0) {
    const initial: Record<string, string> = {};
    factOptions.forEach((f) => {
      if (f.ask_id && f.draft) {
        initial[f.ask_id] = f.draft;
      }
    });
    setContentAnswers(initial);
  }

  return (
    <div
      className={cn(
        wide
          ? "mx-auto w-full max-w-5xl"
          : "rounded-xl border border-border bg-secondary/40 p-3.5"
      )}
    >
      <p
        className={cn(
          "text-foreground",
          wide ? "mb-5 text-lg font-medium tracking-tight" : "mb-3 text-sm"
        )}
      >
        {gate.question}
      </p>

      {/* The palettes measured from the reference sites — context for the
          choice, not one of the choices. */}
      {sourcesSpecimen && (
        <div className={wide ? "mb-6" : "mb-3"}>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">
            Your reference sites
          </p>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {/* The specimen is rendered 1800x1400 with the swatch rows in
              the top third; shown whole it buries the actual choices below
              the fold. Cap the height and crop from the top. */}
          <img
            src={assetUrl(sourcesSpecimen)}
            alt="Colours measured from the reference sites"
            className={cn(
              "w-full rounded-lg border border-border object-cover object-top",
              wide ? "max-h-72" : "max-h-44"
            )}
          />
        </div>
      )}

      {/* Fact questions at the material gate */}
      {isMaterialGate && factOptions.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium text-muted-foreground">
            Confirm these facts about your business
          </p>
          <div className="flex flex-col gap-3">
            {factOptions.map((f) => (
              <div
                key={f.ask_id}
                className="rounded-lg border border-border bg-card/40 p-3"
              >
                <p className="mb-1.5 text-xs text-muted-foreground">
                  {f.question}
                </p>
                <p className="mb-1.5 text-[11px] text-muted-foreground/70">
                  Invented: <span className="italic">{f.invented}</span>
                </p>
                <Input
                  type="text"
                  value={contentAnswers[f.ask_id!] || ""}
                  onChange={(e) =>
                    setContentAnswers({
                      ...contentAnswers,
                      [f.ask_id!]: e.target.value,
                    })
                  }
                  placeholder={f.draft}
                  className="text-sm"
                />
                <p className="mt-1.5 text-[10px] text-muted-foreground/60">
                  Edit to correct, or leave as-is to keep the draft
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {isBriefGate ? (
        // The brief gate asks for exactly one thing — the name — and the
        // server says so in `options[0].choices[0].field = "product_name"`.
        // This used to fall through to the generic branch below, which
        // renders each option as a button: the question about the name was
        // answered with a button labelled "Approve" that sent no name, and
        // the API refused it. A question with a typed answer needs a field.
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (nameOk) onAnswerGate({ product_name: productName.trim() });
          }}
        >
          {nameOption?.why && (
            <p className="text-xs leading-relaxed text-muted-foreground">{nameOption.why}</p>
          )}
          <div className={cn("flex gap-2", wide ? "max-w-md" : "flex-col")}>
            <Input
              autoFocus
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. Ashfall"
              aria-label="Product or business name"
              className="h-9 text-sm"
            />
            <Button type="submit" size="sm" disabled={!nameOk}>
              {nameOption?.choices?.[0]?.label ? "Use this name" : "Continue"}
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground/80">
            Exactly as you write it — it goes into the nav, the footer, the browser tab and
            every screenshot, and nothing downstream may invent one.
          </p>
          {serverError && (
            <p className="text-xs text-destructive">{serverError}</p>
          )}
        </form>
      ) : isDesignGate ? (
        <div
          className={cn(
            "grid gap-3",
            wide ? "grid-cols-1 lg:grid-cols-3 lg:items-start" : "grid-cols-1"
          )}
        >
          {options.map((o, i) => {
            const isOther = o.index === -1 || o.choice === "other";

            if (isOther) {
              return (
                <div
                  key="other"
                  className={cn(
                    "rounded-lg border border-dashed border-border p-3",
                    wide && "lg:col-span-3"
                  )}
                >
                  <p className="text-sm font-medium text-foreground">
                    {o.signature ?? "None of these"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{o.atmosphere}</p>
                  <div className={cn(wide && "flex items-start gap-2")}>
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={2}
                      placeholder="darker, warmer, less green…"
                      className="mt-2 w-full resize-none rounded-md border border-input bg-transparent px-2 py-1.5 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className={cn("mt-2 shrink-0", !wide && "block")}
                      // The backend 400s on an empty note, so gate the button
                      // rather than letting the request fail.
                      disabled={!note.trim()}
                      onClick={() => onAnswerGate({ choice: "other", note: note.trim() })}
                    >
                      Propose three new directions
                    </Button>
                  </div>
                </div>
              );
            }

            return (
              <button
                key={o.index ?? i}
                type="button"
                onClick={() => onAnswerGate({ choice: o.index ?? i })}
                className="group/dir flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card/40 text-left transition-colors hover:border-ring hover:bg-card"
              >
                {/* The rendered palette and type. This is the part a
                    non-designer can actually judge. */}
                {o.specimen && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={assetUrl(o.specimen)}
                    alt={o.signature ?? `Direction ${(o.index ?? i) + 1}`}
                    className="w-full border-b border-border"
                  />
                )}
                <div className={cn("flex flex-1 flex-col p-3", wide && "p-4")}>
                  <p className="text-sm font-medium text-foreground">{o.signature}</p>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                    {o.atmosphere}
                  </p>
                  {o.type && (
                    <p className="mt-auto pt-2 text-xs text-muted-foreground">{o.type}</p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      ) : isMaterialGate ? (
        // Material gate needs special handling for both images and facts
        <div className="flex flex-col gap-4">
          {grouped.map(({ kind, items }) => (
            <div key={kind}>
              <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                {KIND_ICON[kind]}
                {KIND_LABEL[kind]}
                <span className="font-normal opacity-70">
                  · {items.length === 1 ? "one slot" : `${items.length} slots`}
                </span>
              </p>
              <div className="flex flex-col gap-3">
                {items.map((asset) => {
                  const assetId = asset.asset_id ?? String(asset.choice);
                  const current = assetDecisions[assetId];
                  // The server's own list — three for an image, two for a
                  // logo, three for a video — each with its label and the
                  // one-line reason. Rendering this instead of a fixed set of
                  // radios is what makes the logo and video rows answerable.
                  const choices = asset.choices ?? [];
                  const brief = (asset.brief ?? "").replace(/^\[video\]\s*/i, "");
                  return (
                    <div
                      key={assetId}
                      className={cn(
                        "rounded-lg border bg-card/40 p-3 transition-colors",
                        current ? "border-border" : "border-amber-300/30"
                      )}
                    >
                      <div className="mb-1 flex items-baseline justify-between gap-2">
                        <p className="text-sm font-medium text-foreground">
                          {assetId}
                          {asset.prominence && (
                            <span className="ml-2 text-xs font-normal text-muted-foreground">
                              {asset.prominence}
                              {asset.section_id ? ` · ${asset.section_id}` : ""}
                            </span>
                          )}
                        </p>
                        {current && (
                          <span className="flex shrink-0 items-center gap-1 text-[11px] text-emerald-300/90">
                            {outcomeOf(current, kind).icon}
                            {outcomeOf(current, kind).text}
                          </span>
                        )}
                      </div>
                      {brief && (
                        <p className="mb-2.5 text-xs leading-relaxed text-muted-foreground">{brief}</p>
                      )}

                      <div className="flex flex-col gap-2">
                        {choices.map((c) => (
                          <div key={c.choice}>
                            <label className="flex cursor-pointer items-start gap-2">
                              <input
                                type="radio"
                                name={`asset-${assetId}`}
                                value={c.choice}
                                checked={current === c.choice}
                                onChange={() =>
                                  setAssetDecisions({ ...assetDecisions, [assetId]: c.choice })
                                }
                                className="mt-0.5 size-3"
                              />
                              <span className="min-w-0">
                                <span className="block text-xs text-foreground">{c.label}</span>
                                {c.detail && (
                                  <span className="block text-[11px] leading-relaxed text-muted-foreground/80">
                                    {c.detail}
                                  </span>
                                )}
                              </span>
                            </label>

                            {c.choice === "upload" && current === "upload" && (
                              <div className="ml-5 mt-2">
                                <Input
                                  type="file"
                                  accept={ACCEPT[kind]}
                                  onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) {
                                      setUploadedFiles({ ...uploadedFiles, [assetId]: file });
                                    }
                                  }}
                                  className="text-xs"
                                />
                                {uploadedFiles[assetId] && (
                                  <p className="mt-1 text-[10px] text-muted-foreground">
                                    {uploadedFiles[assetId].name} (
                                    {(uploadedFiles[assetId].size / 1024).toFixed(1)}KB)
                                  </p>
                                )}
                                <p className="mt-1 text-[10px] text-muted-foreground/70">
                                  {c.accepts ?? "PNG, JPEG or WebP"}
                                  {kind === "image" && " · restyled to match your design"}
                                  {kind === "video" && " · used as it is, up to 25MB"}
                                  {kind === "logo" && " · used as it is, never redrawn"}
                                  {kind === "portrait" && " · used as it is, never redrawn or generated"}
                                </p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {(uploadError || serverError) && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3">
              <p className="text-xs text-destructive">{uploadError ?? serverError}</p>
            </div>
          )}

          {/* What the run will do once this is answered — the same list the
              assets stage then works through, so nothing that appears later
              is a surprise. */}
          {allDecided && assetOptions.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {(() => {
                const n = (d: string) =>
                  assetOptions.filter((o) => assetDecisions[o.asset_id ?? String(o.choice)] === d);
                const gen = n("generate");
                const genVideo = gen.filter((o) => o.kind === "video").length;
                const genImage = gen.length - genVideo;
                const parts = [
                  genImage > 0 && `${genImage} image${genImage === 1 ? "" : "s"} will be generated`,
                  genVideo > 0 && `${genVideo} video will be generated`,
                  n("upload").length > 0 && `${n("upload").length} of your own file${n("upload").length === 1 ? "" : "s"} used`,
                  n("wordmark").length > 0 && "the name set as a wordmark",
                  n("skip").length > 0 && `${n("skip").length} left out`,
                ].filter(Boolean);
                return parts.join(" · ");
              })()}
            </p>
          )}

          <Button
            type="button"
            variant="default"
            size="sm"
            disabled={uploading || !allDecided}
            onClick={handleMaterialGateSubmit}
          >
            {uploading ? "Uploading…" : "Continue"}
            {!uploading && !allDecided && (
              <span className="ml-1.5 text-xs opacity-70">
                ({decidedCount}/{assetOptions.length} decided)
              </span>
            )}
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {(options.length ? options : [{ choice: "approve", label: "Approve" }]).map(
            (o, i) => (
              <Button
                key={i}
                type="button"
                variant={i === 0 ? "default" : "outline"}
                size="sm"
                onClick={() => onAnswerGate({ choice: o.choice ?? "approve" })}
              >
                {String(o.label ?? o.choice ?? "Approve")}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  );
}
