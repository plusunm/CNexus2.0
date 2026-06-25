"use client";

import { useMindOverview } from "@/cnexus-kernel";
import { useMindTheme } from "../MindUiProvider";
import { useCognitiveCopy } from "@/lib/cognitive";

type Props = {
  pendingConfirmations?: number;
};

export function SimpleStatusCard({ pendingConfirmations = 0 }: Props) {
  const t = useMindTheme();
  const { overview, isLive, isDemo } = useMindOverview();
  const { t: copy } = useCognitiveCopy();

  const memoryCount = overview.memory_items.length;
  const statusLabel = isDemo ? copy("offline") : isLive ? copy("connected") : copy("offline");
  const statusColor = isLive && !isDemo ? t.green : t.orange;

  return (
    <div
      className="rounded-xl border px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <span className="inline-flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: statusColor }} />
        <span style={{ color: t.text }}>{statusLabel}</span>
      </span>
      <span style={{ color: t.textMuted }}>{copy("memoryCount", { count: memoryCount })}</span>
      {pendingConfirmations > 0 && (
        <span style={{ color: t.orange }}>{copy("pendingConfirmations", { count: pendingConfirmations })}</span>
      )}
    </div>
  );
}
