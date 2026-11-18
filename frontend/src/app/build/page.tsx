import { Suspense } from "react";

import { BuildWorkspace } from "@/components/build-workspace";
import { WorkspaceShell } from "@/components/workspace-frame";

/**
 * The workspace reads the project id from the URL, which a static page only
 * knows in the browser, so it renders client-side. The shell is what the
 * server sends meanwhile: the same tab bar, column and panel boxes, so the
 * page paints at once (a real LCP on mobile, where there used to be none)
 * and the hand-over moves nothing (it used to shift by 0.69).
 *
 * The saved chat width is applied by BuildWorkspace's layout effect, before
 * the workspace paints. (An inline <script> here did it for the shell too,
 * but React never runs a script it renders client-side and warned on every
 * navigation from the home screen.)
 */
export default function BuildPage() {
  return (
    <Suspense fallback={<WorkspaceShell />}>
      <BuildWorkspace />
    </Suspense>
  );
}
