import { Suspense } from "react";

import { BuildWorkspace } from "@/components/build-workspace";

export default function BuildPage() {
  return (
    <Suspense>
      <BuildWorkspace />
    </Suspense>
  );
}
