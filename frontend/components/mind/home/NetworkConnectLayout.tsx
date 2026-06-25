"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Globe, Radar, Shield, Link2, Ban, RefreshCw, Users } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { bi, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type TrustedPeerRow = {
  pubkey: string;
  host: string;
  status: string;
  lastSeen?: number;
};

function formatPeerStatus(row: TrustedPeerRow): string {
  const short = row.pubkey.length > 12 ? `${row.pubkey.slice(0, 8)}…${row.pubkey.slice(-6)}` : row.pubkey;
  return `${short} · ${row.status}${row.host ? ` · ${row.host}` : ""}`;
}

export function NetworkConnectLayout() {
  const t = useMindTheme();
  const [network, setNetwork] = useState<Record<string, unknown>>({});
  const [dht, setDht] = useState<Record<string, unknown>>({});
  const [peers, setPeers] = useState<Record<string, Record<string, unknown>>>({});
  const [peerId, setPeerId] = useState("");
  const [banId, setBanId] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setBusy("refresh");
    try {
      const [net, dhtRow, peerRows] = await Promise.all([
        cnexusProductApi.fetchConnectivityStatus(),
        cnexusProductApi.fetchDhtStatus(),
        cnexusProductApi.fetchNetworkPeers(),
      ]);
      setNetwork(net);
      setDht(dhtRow);
      setPeers(peerRows);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const connectivity = (network.connectivity || {}) as Record<string, unknown>;
  const firewall = (network.firewall || {}) as Record<string, unknown>;

  const trustedPeers = useMemo((): TrustedPeerRow[] => {
    return Object.entries(peers)
      .map(([pubkey, row]) => ({
        pubkey,
        host: String(row.host || ""),
        status: String(row.status || "unknown"),
        lastSeen: typeof row.last_seen === "number" ? row.last_seen : undefined,
      }))
      .filter((row) => row.status === "trusted" || row.status === "online")
      .sort((a, b) => (b.lastSeen ?? 0) - (a.lastSeen ?? 0));
  }, [peers]);

  const runConnect = async () => {
    if (!peerId.trim()) return;
    setBusy("connect");
    setMessage("");
    setError("");
    try {
      const row = await cnexusProductApi.connectToPeer(peerId.trim());
      const handshake = (row.handshake || {}) as Record<string, unknown>;
      const pathKind = String(row.path_kind || row.url || "ok");
      if (handshake.ok) {
        setMessage(`${bi(navL.networkConnectOk)} · ${pathKind} · ${bi(navL.networkConnectHandshakeOk)}`);
      } else if (handshake.skipped) {
        setMessage(`${bi(navL.networkConnectOk)} · ${pathKind} · ${bi(navL.networkConnectHandshakeSkip)}`);
      } else {
        setMessage(`${bi(navL.networkConnectOk)} · ${pathKind}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const runBan = async () => {
    if (!banId.trim()) return;
    if (!window.confirm(bi(navL.networkBanConfirm))) return;
    setBusy("ban");
    setMessage("");
    setError("");
    try {
      await cnexusProductApi.banPeer(banId.trim());
      setMessage(bi(navL.networkBanDone));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="space-y-4 w-full min-w-0 max-w-none">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold" style={{ color: t.text }}>
            {bi(navL.networkConnectPageTitle)}
          </h1>
          <p className="text-sm mt-1" style={{ color: t.textMuted }}>
            {bi(navL.networkConnectPageHint)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={busy === "refresh"}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${busy === "refresh" ? "animate-spin" : ""}`} />
          {bi(navL.refresh)}
        </button>
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { icon: Globe, label: bi(navL.networkConnectIce), value: String(connectivity.nat_type || "—") },
          { icon: Radar, label: "DHT", value: String(dht.node_count ?? 0) },
          { icon: Shield, label: bi(navL.networkFirewall), value: String(firewall.local_bans ?? 0) },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-xl border p-3"
            style={{ borderColor: t.border, backgroundColor: t.surface }}
          >
            <card.icon className="w-4 h-4 mb-1" style={{ color: t.blue }} />
            <p className="text-[10px] uppercase" style={{ color: t.textLight }}>
              {card.label}
            </p>
            <p className="text-lg font-semibold" style={{ color: t.text }}>
              {card.value}
            </p>
          </div>
        ))}
      </section>

      <section
        className="rounded-xl border p-3 space-y-2"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <p className="text-xs font-medium flex items-center gap-1.5" style={{ color: t.text }}>
          <Users className="w-4 h-4" style={{ color: t.green }} />
          {bi(navL.networkTrustedPeersTitle)}
          <span className="text-[10px] font-normal" style={{ color: t.textMuted }}>
            ({trustedPeers.length})
          </span>
        </p>
        {trustedPeers.length === 0 ? (
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            {bi(navL.networkTrustedPeersEmpty)}
          </p>
        ) : (
          <ul className="space-y-1 max-h-32 overflow-y-auto">
            {trustedPeers.map((row) => (
              <li
                key={row.pubkey}
                className="text-[10px] font-mono px-2 py-1 rounded border truncate"
                style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.chatBg }}
                title={row.pubkey}
              >
                {formatPeerStatus(row)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        className="rounded-xl border p-3 space-y-3"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <p className="text-xs font-medium flex items-center gap-1.5" style={{ color: t.text }}>
          <Link2 className="w-4 h-4" style={{ color: "#5eead4" }} />
          {bi(navL.networkConnectPeerTitle)}
        </p>
        <p className="text-[11px]" style={{ color: t.textMuted }}>
          {bi(navL.networkConnectPeerHint)}
        </p>
        <input
          value={peerId}
          onChange={(e) => setPeerId(e.target.value)}
          placeholder="peer Ed25519 pubkey (64 hex)"
          className="w-full rounded-lg border px-2 py-1.5 text-xs font-mono"
          style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
        />
        <button
          type="button"
          disabled={Boolean(busy) || !peerId.trim()}
          onClick={() => void runConnect()}
          className="px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
          style={{ borderColor: t.border, color: t.text }}
        >
          {busy === "connect" ? "…" : bi(navL.networkConnectPeerRun)}
        </button>
      </section>

      <section
        className="rounded-xl border p-3 space-y-3"
        style={{ borderColor: `${t.orange}55`, backgroundColor: `${t.orange}08` }}
      >
        <p className="text-xs font-medium flex items-center gap-1.5" style={{ color: t.orange }}>
          <Ban className="w-4 h-4" />
          {bi(navL.networkBanTitle)}
        </p>
        <p className="text-[11px]" style={{ color: t.textMuted }}>
          {bi(navL.networkBanHint)}
        </p>
        <input
          value={banId}
          onChange={(e) => setBanId(e.target.value)}
          placeholder="malicious peer pubkey"
          className="w-full rounded-lg border px-2 py-1.5 text-xs font-mono"
          style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
        />
        <button
          type="button"
          disabled={Boolean(busy) || !banId.trim()}
          onClick={() => void runBan()}
          className="px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
          style={{ borderColor: t.orange, color: t.orange }}
        >
          {busy === "ban" ? "…" : bi(navL.networkBanRun)}
        </button>
      </section>

      <section
        className="rounded-xl border p-2 text-[10px] font-mono max-h-40 overflow-y-auto"
        style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.textMuted }}
      >
        <pre className="whitespace-pre-wrap">{JSON.stringify({ connectivity, dht, firewall, peers }, null, 2)}</pre>
      </section>

      {(message || error) && (
        <p className="text-[11px]" style={{ color: error ? t.orange : t.green }}>
          {error || message}
        </p>
      )}
    </div>
  );
}
