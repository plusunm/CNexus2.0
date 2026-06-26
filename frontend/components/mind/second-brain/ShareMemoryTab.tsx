"use client";

import { SbRemoteMemoryPanel } from "./SbRemoteMemoryPanel";
import { ScopedMemoryFlowGraph3D } from "../shared/ScopedMemoryFlowGraph3D";
import { useSyncMemoryScope } from "@/hooks/useSyncMemoryScope";

export function ShareMemoryTab() {
  const [scope, setScope] = useSyncMemoryScope();

  return (
    <div className="flex flex-col gap-5 pb-8 w-full min-w-0 cnexus-float-scroll">
      <ScopedMemoryFlowGraph3D scope={scope} onScopeChange={setScope} variant="page" className="shrink-0" />
      <SbRemoteMemoryPanel asPage scope={scope} onScopeChange={setScope} hideScopeSelector />
    </div>
  );
}
