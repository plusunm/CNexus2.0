"use client";

import { SbNetworkTopologyPanel } from "./SbNetworkTopologyPanel";

export function NetworkTab() {
  return (
    <div className="flex flex-col pb-8 cnexus-float-scroll">
      <SbNetworkTopologyPanel asPage />
    </div>
  );
}
