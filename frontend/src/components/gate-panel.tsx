"use client";

import { useState } from "react";

import {
  assetUrl,
  uploadAsset,
  type Direction,
  type GateInfo,
  type GateOption,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
  onAnswerGate,
}: {
  gate: GateInfo;
  directions: Direction[] | null;
  layout: "wide" | "compact";
  projectId: string;
  onAnswerGate: (payload: {
    choice?: string | number;
    note?: string;
    assets?: Record<string, string>;
    content?: Record<string, string>;
  }) => void;
}) {
  const [note, setNote] = useState("");
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
  const isDesignGate = gate.gate === "gate:design";
  const isMaterialGate = gate.gate === "gate:assets";

  // Split material gate options into images and facts
  const imageOptions = options.filter((o) => !o.kind || o.kind === "image");
  const factOptions = options.filter((o) => o.kind === "fact");

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

      {isDesignGate ? (
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
          {imageOptions.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                Images for this page
              </p>
              <div className="flex flex-col gap-3">
                {imageOptions.map((img) => {
                  const assetId = (img as any).asset_id || img.choice;
                  const brief = (img as any).brief || "";
                  const prominence = (img as any).prominence || "";
                  const currentDecision = assetDecisions[assetId];
                  
                  return (
                    <div
                      key={assetId}
                      className="rounded-lg border border-border bg-card/40 p-3"
                    >
                      <p className="mb-1 text-sm font-medium text-foreground">
                        {assetId}
                        {prominence && (
                          <span className="ml-2 text-xs text-muted-foreground">
                            ({prominence})
                          </span>
                        )}
                      </p>
                      {brief && (
                        <p className="mb-2 text-xs text-muted-foreground">{brief}</p>
                      )}
                      <div className="flex flex-col gap-2">
                        {/* Upload option */}
                        <div>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name={`asset-${assetId}`}
                              value="upload"
                              checked={currentDecision === "upload"}
                              onChange={(e) =>
                                setAssetDecisions({
                                  ...assetDecisions,
                                  [assetId]: e.target.value,
                                })
                              }
                              className="size-3"
                            />
                            <span className="text-xs text-foreground">Use my own image</span>
                          </label>
                          {currentDecision === "upload" && (
                            <div className="mt-2 ml-5">
                              <Input
                                type="file"
                                accept="image/png,image/jpeg,image/webp"
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (file) {
                                    setUploadedFiles({
                                      ...uploadedFiles,
                                      [assetId]: file,
                                    });
                                  }
                                }}
                                className="text-xs"
                              />
                              {uploadedFiles[assetId] && (
                                <p className="mt-1 text-[10px] text-muted-foreground">
                                  {uploadedFiles[assetId].name} ({(uploadedFiles[assetId].size / 1024).toFixed(1)}KB)
                                </p>
                              )}
                              <p className="mt-1 text-[10px] text-muted-foreground/70">
                                PNG, JPEG, or WebP up to 25MB. Will be restyled to match your design.
                              </p>
                            </div>
                          )}
                        </div>
                        
                        {/* Generate option */}
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name={`asset-${assetId}`}
                            value="generate"
                            checked={currentDecision === "generate"}
                            onChange={(e) =>
                              setAssetDecisions({
                                ...assetDecisions,
                                [assetId]: e.target.value,
                              })
                            }
                            className="size-3"
                          />
                          <span className="text-xs text-foreground">Generate from description</span>
                        </label>
                        
                        {/* Skip option */}
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name={`asset-${assetId}`}
                            value="skip"
                            checked={currentDecision === "skip"}
                            onChange={(e) =>
                              setAssetDecisions({
                                ...assetDecisions,
                                [assetId]: e.target.value,
                              })
                            }
                            className="size-3"
                          />
                          <span className="text-xs text-foreground">No image - build from layout only</span>
                        </label>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {uploadError && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3">
              <p className="text-xs text-destructive">{uploadError}</p>
            </div>
          )}
          
          <Button
            type="button"
            variant="default"
            size="sm"
            disabled={uploading || (imageOptions.length > 0 && Object.keys(assetDecisions).length < imageOptions.length)}
            onClick={handleMaterialGateSubmit}
          >
            {uploading ? "Uploading..." : "Continue"}
            {!uploading && imageOptions.length > 0 && 
              Object.keys(assetDecisions).length < imageOptions.length && (
                <span className="ml-1.5 text-xs opacity-70">
                  ({Object.keys(assetDecisions).length}/{imageOptions.length} decided)
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
