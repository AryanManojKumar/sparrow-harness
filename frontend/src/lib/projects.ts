/**
 * Recent-projects fixture. Stands in for GET /runs until the backend exists —
 * see backend/src/sparrow/blackboard/store.py, which already versions every
 * project this list would enumerate.
 */

export type ProjectSummary = {
  id: string;
  name: string;
  updatedLabel: string;
  status: "building" | "ready" | "needs input";
};

export const RECENT_PROJECTS: ProjectSummary[] = [
  { id: "ledgerline", name: "Ledgerline", updatedLabel: "Updated 3 days ago", status: "ready" },
];
