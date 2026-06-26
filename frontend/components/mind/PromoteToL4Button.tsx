"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import { useMindStore } from "@/cnexus-kernel";
import { brainApi } from "@/lib/api";
import { canPromoteToFoundation, MEMORY_LEVEL_LABEL, resolveMemoryLevel } from "@/lib/memoryPromote";
import type { MindOverviewMemoryItem } from "@/lib/runtimeTypes";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  item: MindOverviewMemoryItem;
  disabled?: boolean;
  compact?: boolean;
  className?: string;
};

/** One-click promote to Foundation (L4). */
export function PromoteToL4Button({ item, disabled = false, compact = false, className = "" }: Props) {
  const t = useMindTheme();
  const pullMindOverview = useMindStore((s) => s.pullMindOverview);
  const [busy, setBusy] = useState(false);

  if (!canPromoteToFoundation(item)) return null;

  const current = resolveMemoryLevel(item);
  const currentLabel = current ? MEMORY_LEVEL_LABEL[current] || current : "L2";

  const handleClick = async () => {
    if (busy || disabled) return;
    const ok = window.confirm(
      `将此记忆提升为 Foundation（L4 基石）？\n\n当前：${currentLabel}\n标题：${item.title}`,
    );
    if (!ok) return;
    setBusy(true);
    try {
      await brainApi.promoteMemory(item.id, "foundation", true);
      await pullMindOverview();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "提升失败");
    } finally {
      setBusy(false);
    }
  };

  if (compact) {
    return (
      <button
        type="button"
        title="提升到 L4（Foundation）"
        disabled={busy || disabled}
        onClick={() => void handleClick()}
        className={`p-0.5 disabled:opacity-40 ${className}`}
      >
        <Shield className="w-3.5 h-3.5" style={{ color: "#a78bfa" }} />
      </button>
    );
  }

  return (
    <button
      type="button"
      disabled={busy || disabled}
      onClick={() => void handleClick()}
      className={`text-[10px] px-2 py-0.5 rounded-md border font-medium disabled:opacity-50 shrink-0 ${className}`}
      style={{
        borderColor: "#a78bfa55",
        color: "#a78bfa",
        backgroundColor: "rgba(167,139,250,0.08)",
      }}
    >
      {busy ? "提升中…" : "提升到 L4"}
    </button>
  );
}
