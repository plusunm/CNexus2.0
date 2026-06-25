"use client";

import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { SbCard } from "./SbUIKit";

export function ChatShareTab() {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();

  return (
    <div className="flex flex-col gap-4 pb-8 cnexus-float-scroll">
      <SbCard padding="sm">
        <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
          {copy("shareChatShareBody")}
        </p>
      </SbCard>
    </div>
  );
}
