"use client";

import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { DingTalkSettingsPanel } from "../DingTalkSettingsPanel";
import { SbCard } from "./SbUIKit";

export function NotifyTab() {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();

  return (
    <div className="flex flex-col gap-4 pb-8 cnexus-float-scroll">
      <SbCard accent="teal">
        <p className="text-xs mb-4 leading-relaxed" style={{ color: t.textMuted }}>
          {copy("shareExternalNotifyHint")}
        </p>
        <DingTalkSettingsPanel />
      </SbCard>
    </div>
  );
}
