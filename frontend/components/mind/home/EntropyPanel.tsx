"use client";

import { useCallback, useEffect, useState } from "react";
import { Flame, RefreshCw } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { bi, navL } from "@/lib/spine/labels";
import type { DashboardStatus } from "@/lib/dashboardTypes";
import { useMindTheme } from "../MindUiProvider";

type EntropyPanelProps = {
  entropy?: DashboardStatus["entropy"];
};

export function EntropyPanel({ entropy: initial }: EntropyPanelProps) {
  const t = useMindTheme();
  const [loading, setLoading] = useState(false);
  const [entropy, setEntropy] = useState(initial);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const row = await cnexusProductApi.fetchEntropyStatus();
      setEntropy(row as DashboardStatus["entropy"]);
    } catch {
      /* keep last */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setEntropy(initial);
  }, [initial]);

  useEffect(() => {
    if (!initial) void load();
  }, [initial, load]);

  return (
    <section
      className="rounded-xl border p-3 space-y-3"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-start gap-2">
          <Flame className="w-4 h-4 mt-0.5" style={{ color: t.orange }} />
          <div>
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {bi(navL.missionControlEntropy)}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: t.textMuted }}>
              {bi(navL.missionControlEntropyHint)}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          {bi(navL.refresh)}
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
        {[
          { label: "状态", value: entropy?.enabled ? "ON" : "OFF" },
          { label: "全局熵", value: entropy?.global_entropy || "—" },
          { label: "温度 T", value: entropy?.temperature != null ? String(entropy.temperature) : "—" },
          { label: "Peer seeds", value: entropy?.trusted_peer_seeds ?? "—" },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-lg border px-2 py-1.5"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <p style={{ color: t.textLight }}>{card.label}</p>
            <p className="mt-0.5 font-mono truncate" style={{ color: t.text }}>
              {card.value}
            </p>
          </div>
        ))}
      </div>
      <p className="text-[10px] font-mono truncate" style={{ color: t.textMuted }}>
        local {entropy?.local_seed || "—"}
      </p>
    </section>
  );
}
