"use client";

import { SbRemoteMemoryPanel } from "./SbRemoteMemoryPanel";

export function ShareMemoryTab() {
  return (
    <div className="flex flex-col pb-8 cnexus-float-scroll">
      <SbRemoteMemoryPanel asPage />
    </div>
  );
}
