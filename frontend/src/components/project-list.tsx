"use client";

import { useEffect, useState } from "react";

import { listProjects, type ProjectSummary } from "@/lib/api";
import { ProjectCard } from "@/components/project-card";

export function ProjectList() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    listProjects()
      .then((rows) => live && setProjects(rows))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  // Nothing to say on a first run, and nothing useful to say when the
  // backend simply isn't up — either way the home screen stays clean rather
  // than showing an error the user can't act on from here.
  if (failed || (projects && projects.length === 0)) return null;

  return (
    <section className="mx-auto mt-24 w-full max-w-5xl">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-foreground">Your projects</h2>
        {projects && (
          <span className="text-xs text-muted-foreground">{projects.length}</span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects
          ? // The API already sorts newest-first; keep its order.
            projects.map((p) => <ProjectCard key={p.project_id} project={p} />)
          : Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="overflow-hidden rounded-xl border border-border bg-card/20"
              >
                <div className="aspect-[16/10] animate-pulse border-b border-border bg-muted/40" />
                <div className="space-y-2 p-3.5">
                  <div className="h-3 w-1/2 animate-pulse rounded bg-muted/40" />
                  <div className="h-2.5 w-2/3 animate-pulse rounded bg-muted/30" />
                </div>
              </div>
            ))}
      </div>
    </section>
  );
}
