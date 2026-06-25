"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import clsx from "clsx";
import { brainApi } from "@/lib/api";
import { useMindOverview, useMindStore } from "@/cnexus-kernel";
import { clearChatMessages } from "@/lib/chatHistoryStorage";
import { isPersonalMode } from "@/lib/personalGuard";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  compact?: boolean;
  className?: string;
};

export function ClearMemoryButton({ compact, className }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const { isDemo, isLive, isFallback } = useMindOverview();
  const pullMindOverview = useMindStore((s) => s.pullMindOverview);
  const [busy, setBusy] = useState(false);

  if (!isPersonalMode()) return null;

  const disabled = isDemo || busy || (!isLive && !isFallback);

  const handleClick = async () => {
    if (disabled) return;
    if (!window.confirm(copy("clearMemoryConfirm"))) return;
    setBusy(true);
    try {
      await brainApi.v2ClearMemory(true);
      clearChatMessages();
      await pullMindOverview();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : copy("clearMemoryFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => void handleClick()}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium disabled:opacity-50 transition",
        compact ? "w-full py-2 text-xs border" : "px-2.5 py-1.5 text-[11px] border",
        className,
      )}
      style={{
        borderColor: disabled ? t.border : "#f87171",
        color: disabled ? t.textMuted : "#f87171",
        backgroundColor: disabled ? "transparent" : "rgba(248,113,113,0.08)",
      }}
    >
      <Trash2 className={compact ? "w-3.5 h-3.5" : "w-3.5 h-3.5"} />
      {busy ? copy("clearMemoryBusy") : copy("clearMemory")}
    </button>
  );
}
