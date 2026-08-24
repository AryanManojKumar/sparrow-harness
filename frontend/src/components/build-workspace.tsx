"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { BuildFeed } from "@/components/build-feed";
import { PreviewPane } from "@/components/preview-pane";
import { initialSections, runMockBuild, type SectionState } from "@/lib/build-feed";
import type { Source } from "@/lib/sources";

export function BuildWorkspace() {
  const params = useSearchParams();
  const prompt = params.get("p") || "Your business, described in one line.";
  const sourceParam = params.get("source");
  let source: Source | null = null;
  if (sourceParam) {
    try {
      source = JSON.parse(sourceParam) as Source;
    } catch {
      source = null;
    }
  }

  const [sections, setSections] = useState<SectionState[]>(initialSections());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const cancel = runMockBuild(setSections, () => setReady(true));
    return cancel;
  }, []);

  return (
    <div className="grid h-screen grid-cols-1 md:grid-cols-[360px_1fr]">
      <div className="border-r border-border bg-card/30">
        <BuildFeed prompt={prompt} sections={sections} source={source} />
      </div>
      <PreviewPane ready={ready} />
    </div>
  );
}
