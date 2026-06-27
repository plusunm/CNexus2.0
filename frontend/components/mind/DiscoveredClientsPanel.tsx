"use client";

import { useCallback, useEffect, useState } from "react";
import { Link2, Radar, RefreshCw } from "lucide-react";
import { cnexusProductApi, type DiscoveredClientRow } from "@/lib/api";
import { parseConnectApplication, type ApplicationConnectSnapshot } from "@/lib/applicationControl";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";
import { RepairGatePanel } from "./shared/RepairGatePanel";

type Props = {
  compact?: boolean;
  className?: string;
};

function sourceLabel(sources: string[] | undefined): string {
  const list = sources?.length ? sources : [];
  const labels: string[] = [];
  if (list.includes("lan")) labels.push("局域网");
  if (list.includes("dht")) labels.push("DHT");
  if (list.includes("registry")) labels.push("邻居表");
  return labels.join(" · ") || "—";
}

function statusLabel(row: DiscoveredClientRow): string {
  if (row.trusted) return row.status === "online" ? "在线 · 已信任" : "已信任";
  if (row.status === "online") return "在线";
  if (row.status === "discovered") return "已发现";
  return row.status || "未知";
}

export function DiscoveredClientsPanel({ compact, className = "" }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [clients, setClients] = useState<DiscoveredClientRow[]>([]);
  const [meta, setMeta] = useState<{ count?: number; lan_found?: number; refreshed?: boolean }>({});
  const [busy, setBusy] = useState(false);
  const [connectBusy, setConnectBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [repairSnapshot, setRepairSnapshot] = useState<ApplicationConnectSnapshot | null>(null);

  const load = useCallback(async (refresh = false) => {
    setBusy(true);
    setError("");
    try {
      const data = await cnexusProductApi.fetchDiscoveredClients(refresh);
      setClients(data.clients ?? []);
      setMeta({
        count: data.count,
        lan_found: data.lan_found,
        refreshed: data.refreshed,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load(false);
  }, [load]);

  const connectClient = async (pubkey: string) => {
    setConnectBusy(pubkey);
    setMessage("");
    setError("");
    setRepairSnapshot(null);
    try {
      const row = await cnexusProductApi.connectToPeer(pubkey);
      setMessage(copy("shareConnectOk"));
      const appSnapshot = parseConnectApplication(row);
      if (appSnapshot) setRepairSnapshot(appSnapshot);
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setConnectBusy(null);
    }
  };

  return (
    <section
      className={`rounded-xl border space-y-3 ${compact ? "p-3" : "p-4"} ${className}`}
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p
            className={`font-semibold flex items-center gap-1.5 ${compact ? "text-xs" : "text-sm"}`}
            style={{ color: t.text }}
          >
            <Radar className="w-4 h-4 shrink-0" style={{ color: "#5eead4" }} />
            {copy("shareDiscoveredClients")}
            <span className="font-normal" style={{ color: t.textMuted }}>
              ({meta.count ?? clients.length})
            </span>
          </p>
          <p className={`mt-1 leading-relaxed ${compact ? "text-[10px]" : "text-[11px]"}`} style={{ color: t.textMuted }}>
            {copy("shareDiscoveredClientsHint")}
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => void load(true)}
          className={`inline-flex items-center gap-1 shrink-0 px-2.5 py-1.5 rounded-lg border disabled:opacity-50 ${
            compact ? "text-[10px]" : "text-xs"
          }`}
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${busy ? "animate-spin" : ""}`} />
          {copy("shareScanDiscovered")}
        </button>
      </div>

      {meta.refreshed && meta.lan_found != null && meta.lan_found > 0 ? (
        <p className="text-[10px]" style={{ color: t.green }}>
          局域网扫描发现 {meta.lan_found} 台 CNexus
        </p>
      ) : null}

      {clients.length === 0 ? (
        <p className={`${compact ? "text-[10px]" : "text-xs"}`} style={{ color: t.textMuted }}>
          {copy("shareDiscoveredEmpty")}
        </p>
      ) : (
        <ul className={`space-y-2 overflow-y-auto ${compact ? "max-h-[200px]" : "max-h-[280px]"}`}>
          {clients.map((row) => (
            <li
              key={row.pubkey}
              className="rounded-xl border px-3 py-2.5 flex items-start justify-between gap-2"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium truncate" style={{ color: t.text }}>
                  {row.host || row.pubkey_short || row.pubkey}
                </p>
                <p className="text-[10px] font-mono truncate mt-0.5" style={{ color: t.textMuted }} title={row.pubkey}>
                  {row.pubkey_short || row.pubkey}
                </p>
                <p className="text-[10px] mt-1" style={{ color: t.textLight }}>
                  {statusLabel(row)} · {sourceLabel(row.sources)}
                </p>
              </div>
              {!row.trusted ? (
                <button
                  type="button"
                  disabled={connectBusy === row.pubkey}
                  onClick={() => void connectClient(row.pubkey)}
                  className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium border disabled:opacity-50"
                  style={{ borderColor: `${t.blue}66`, color: t.blue }}
                >
                  <Link2 className="w-3 h-3" />
                  {connectBusy === row.pubkey ? "…" : copy("shareConnectThisDevice")}
                </button>
              ) : (
                <span className="shrink-0 text-[10px] px-2 py-1 rounded-md" style={{ color: "#5eead4", backgroundColor: "#14b8a618" }}>
                  已连接
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {repairSnapshot ? <RepairGatePanel snapshot={repairSnapshot} onComplete={() => void load(false)} /> : null}

      {(message || error) && (
        <p className="text-[11px]" style={{ color: error ? t.orange : t.green }}>
          {error || message}
        </p>
      )}
    </section>
  );
}
