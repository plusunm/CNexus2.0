"use client";

import { useState } from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { bi, navL } from "@/lib/spine/labels";
import type { DashboardAwakening } from "@/lib/dashboardTypes";
import { useMindTheme } from "../MindUiProvider";

const PHASES = [
  { id: "genesis", labelKey: navL.missionControlAwakeningGenesis },
  { id: "replay", labelKey: navL.missionControlAwakeningReplay },
  { id: "vector_index", labelKey: navL.missionControlAwakeningVector },
] as const;

function phaseState(phase: string, current: string, alive: boolean) {
  const order = ["genesis", "replay", "vector_index", "alive"];
  const currentIdx = order.indexOf(current);
  const phaseIdx = order.indexOf(phase);
  if (alive && current === "alive") return "done";
  if (current === phase) return "active";
  if (currentIdx > phaseIdx && phaseIdx >= 0) return "done";
  return "pending";
}

type AwakeningPanelProps = {
  awakening?: DashboardAwakening;
  onComplete?: () => void;
};

export function AwakeningPanel({ awakening, onComplete }: AwakeningPanelProps) {
  const t = useMindTheme();
  const [busy, setBusy] = useState("");
  const [hint, setHint] = useState("");

  if (!awakening) return null;

  const phase = awakening.phase || "idle";
  const alive = Boolean(awakening.alive);
  const show = !alive || phase === "alive" || (awakening.progress ?? 0) > 0;
  if (!show && phase === "idle") return null;

  const progress = Math.round((awakening.progress ?? 0) * 100);

  const retryReplay = async () => {
    setBusy("replay");
    setHint("");
    try {
      const row = await cnexusProductApi.runLogReplay(true);
      setHint(String(row.summary || row.message || "replay ok"));
      onComplete?.();
    } catch (err) {
      setHint(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const retryReindex = async () => {
    setBusy("reindex");
    setHint("");
    try {
      const row = await cnexusProductApi.reindexAssets();
      setHint(`indexed=${row.indexed ?? "?"}`);
      onComplete?.();
    } catch (err) {
      setHint(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <section
      className="rounded-xl border p-3 space-y-3"
      style={{
        borderColor: alive ? `${t.green}66` : t.border,
        backgroundColor: alive ? `${t.green}10` : t.surface,
      }}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4" style={{ color: alive ? t.green : t.purple }} />
          <div>
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {bi(navL.missionControlAwakening)}
              {alive ? ` · ${bi(navL.missionControlAwakeningAlive)}` : ""}
            </p>
            <p className="text-[11px]" style={{ color: t.textMuted }}>
              {awakening.message || awakening.summary || bi(navL.missionControlAwakeningHint)}
            </p>
          </div>
        </div>
        {!alive && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={Boolean(busy)}
              onClick={() => void retryReplay()}
              className="text-[10px] px-2 py-1 rounded border disabled:opacity-50"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              {busy === "replay" ? "…" : bi(navL.missionControlAwakeningRetryReplay)}
            </button>
            <button
              type="button"
              disabled={Boolean(busy)}
              onClick={() => void retryReindex()}
              className="text-[10px] px-2 py-1 rounded border disabled:opacity-50"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              {busy === "reindex" ? "…" : bi(navL.missionControlAwakeningRetryReindex)}
            </button>
          </div>
        )}
      </div>

      <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: t.chatBg }}>
        <div
          className="h-full transition-all duration-500"
          style={{
            width: `${Math.max(progress, alive ? 100 : 8)}%`,
            background: alive
              ? `linear-gradient(90deg, ${t.green}, ${t.blue})`
              : `linear-gradient(90deg, ${t.purple}, ${t.blue})`,
          }}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
        {PHASES.map((row) => {
          const state = phaseState(row.id, phase, alive);
          const color = state === "done" ? t.green : state === "active" ? t.blue : t.textMuted;
          return (
            <div
              key={row.id}
              className="rounded-lg border px-2 py-1.5"
              style={{
                borderColor: state === "active" ? `${t.blue}55` : t.border,
                backgroundColor: state === "active" ? `${t.blue}10` : t.chatBg,
                color,
              }}
            >
              {bi(row.labelKey)}
            </div>
          );
        })}
      </div>

      {hint && (
        <p className="text-[10px] truncate" style={{ color: t.textMuted }}>
          {hint}
        </p>
      )}
    </section>
  );
}
