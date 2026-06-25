"use client";

import { bi, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { AssetIngestPanel } from "./AssetIngestPanel";
import { SelfReflectionPanel } from "./SelfReflectionPanel";

export function NetworkAssetsLayout() {
  const t = useMindTheme();
  return (
    <div className="space-y-4 w-full min-w-0 max-w-none">
      <header>
        <h1 className="text-xl font-bold" style={{ color: t.text }}>
          {bi(navL.networkAssetsPageTitle)}
        </h1>
        <p className="text-sm mt-1" style={{ color: t.textMuted }}>
          {bi(navL.networkAssetsPageHint)}
        </p>
      </header>
      <AssetIngestPanel />
      <SelfReflectionPanel />
    </div>
  );
}
