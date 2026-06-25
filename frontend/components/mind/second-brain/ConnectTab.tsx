"use client";

import { SbPeerConnectPanel } from "./SbPeerConnectPanel";

export function ConnectTab() {
  return (
    <div className="flex flex-col pb-8 cnexus-float-scroll">
      <SbPeerConnectPanel asPage />
    </div>
  );
}
