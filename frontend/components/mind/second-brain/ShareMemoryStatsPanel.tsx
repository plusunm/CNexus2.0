"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3, RefreshCw, Share2 } from "lucide-react";
import { cnexusProductApi, type ShareStatsStatus } from "@/lib/api";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { SbCard, SbSection } from "./SbUIKit";

function fmtTime(ts?: number | null) {
  if (!ts) return "—";
  try {
    return new Date(ts * 1000).toLocaleString();
  } catch {
    return "—";
  }
}

export function ShareMemoryStatsPanel() {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const title = copy("shareMemoryStatsTitle");
  const hint = copy("shareMemoryStatsHint");
  const localBlocksLabel = copy("shareMemoryStatsLocalBlocks");
  const visibleGraphsLabel = copy("shareMemoryStatsVisibleGraphs");
  const visibleClientsLabel = copy("shareMemoryStatsVisibleSharingClients");
  const autoShareOn = copy("shareMemoryStatsAutoShareOn");
  const autoShareOff = copy("shareMemoryStatsAutoShareOff");
  const publishNowLabel = copy("shareMemoryStatsPublishNow");
  const refreshLabel = copy("shareMemoryStatsRefresh");

  const [stats, setStats] = useState<ShareStatsStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setStats(await cnexusProductApi.fetchShareStats());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const publishNow = async () => {
    setBusy(true);
    setError("");
    try {
      await cnexusProductApi.publishLocalMemory();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const visible = stats?.visible;
  const sharingOn = Boolean(stats?.sharing_enabled);

  const statTiles = [
    { label: localBlocksLabel, value: stats?.local_memory_blocks ?? stats?.block_count ?? 0 },
    { label: visibleGraphsLabel, value: visible?.graph_count ?? stats?.catalog?.graph_count ?? 0 },
    { label: visibleClientsLabel, value: visible?.sharing_client_count ?? 0 },
  ];

  return (
    <SbSection title={title} icon={BarChart3}>
      <SbCard padding="sm">
        <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
          {hint}
        </p>

        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2">
          {statTiles.map((tile) => (
            <div
              key={tile.label}
              className="rounded-lg border px-2.5 py-2"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <p className="text-[10px]" style={{ color: t.textMuted }}>
                {tile.label}
              </p>
              <p className="text-lg font-semibold tabular-nums mt-0.5" style={{ color: t.text }}>
                {tile.value}
              </p>
            </div>
          ))}
        </div>

        <div
          className="mt-3 flex flex-wrap items-center gap-2 text-[10px]"
          style={{ color: t.textLight }}
        >
          <span>{sharingOn ? autoShareOn : autoShareOff}</span>
          {stats?.graph_id ? (
            <span className="font-mono truncate max-w-full">
              graph {String(stats.graph_id).slice(0, 12)}… · {stats.block_count ?? 0} blocks
            </span>
          ) : null}
          {stats?.last_shared_at ? <span>· {fmtTime(stats.last_shared_at)}</span> : null}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void publishNow()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-50"
            style={{ backgroundColor: "#14b8a6", color: "#fff" }}
          >
            <Share2 className="w-3.5 h-3.5" />
            {publishNowLabel}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void refresh()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${busy ? "animate-spin" : ""}`} />
            {refreshLabel}
          </button>
        </div>

        {error ? (
          <p className="text-[10px] mt-2" style={{ color: t.orange }}>
            {error}
          </p>
        ) : null}
      </SbCard>
    </SbSection>
  );
}
