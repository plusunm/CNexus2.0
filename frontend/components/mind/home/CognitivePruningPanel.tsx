"use client";

import { useState } from "react";
import { Scissors, RefreshCw } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { useCognitiveCopy } from "@/lib/cognitive";
import type { DashboardStatus } from "@/lib/dashboardTypes";
import { useMindTheme } from "../MindUiProvider";

type CognitivePruningPanelProps = {
  pruning?: DashboardStatus["pruning"];
  onComplete?: () => void;
};

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

export function CognitivePruningPanel({ pruning, onComplete }: CognitivePruningPanelProps) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<{ archived_blocks?: number; summaries_created?: number } | null>(null);
  const [lastReport, setLastReport] = useState<{ archived_blocks?: number; summaries_created?: number } | null>(
    pruning?.last_report || null,
  );

  const run = async (dryRun: boolean) => {
    setBusy(dryRun ? "preview" : "run");
    setError("");
    try {
      const row = await cnexusProductApi.runCognitivePruning(dryRun);
      const report = (row.report || {}) as { archived_blocks?: number; summaries_created?: number };
      if (dryRun) {
        setPreview(report);
      } else {
        setLastReport(report);
        setPreview(null);
        onComplete?.();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <section
      className="rounded-xl border p-3 space-y-3"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-start gap-2">
          <Scissors className="w-4 h-4 mt-0.5" style={{ color: t.blue }} />
          <div>
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {copy("pruning")}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: t.textMuted }}>
              {copy("activeMemory")} · {copy("archivedMemory")} · {copy("knowledgeConclusion")}
            </p>
            <p className="text-[10px] mt-1" style={{ color: t.textLight }}>
              {pruning?.enabled ? "ON" : "OFF"} · {copy("activeMemory")} {pruning?.active_blocks ?? "—"} ·{" "}
              {copy("archivedMemory")} {pruning?.total_archived ?? 0} · {copy("knowledgeConclusion")}{" "}
              {pruning?.knowledge_conclusions ?? 0}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void run(true)}
            disabled={Boolean(busy) || pruning?.enabled === false}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            {busy === "preview" ? "…" : copy("pruningPreview")}
          </button>
          <button
            type="button"
            onClick={() => void run(false)}
            disabled={Boolean(busy) || pruning?.enabled === false}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${busy === "run" ? "animate-spin" : ""}`} />
            {copy("pruningRun")}
          </button>
        </div>
      </div>

      {preview && (
        <p className="text-[11px] rounded-lg border px-2 py-1.5" style={{ borderColor: t.blue, color: t.blue }}>
          预览：摘要 +{preview.summaries_created ?? 0} · 归档 -{preview.archived_blocks ?? 0}
        </p>
      )}

      {error && (
        <p className="text-[11px] rounded-lg border px-2 py-1.5" style={{ borderColor: t.orange, color: t.orange }}>
          {error}
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
        {[
          { label: "引用追踪", value: pruning?.ref_tracked ?? 0 },
          { label: "争议追踪", value: pruning?.dispute_tracked ?? 0 },
          { label: "上次修剪", value: formatTime(pruning?.last_run_at) },
          {
            label: "最近批次",
            value: lastReport
              ? `+${lastReport.summaries_created ?? 0} / -${lastReport.archived_blocks ?? 0}`
              : "—",
          },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-lg border px-2 py-1.5"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <p style={{ color: t.textLight }}>{card.label}</p>
            <p className="mt-0.5 truncate" style={{ color: t.text }}>
              {card.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
