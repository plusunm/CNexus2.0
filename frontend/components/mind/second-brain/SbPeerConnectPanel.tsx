"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Ban, Link2, Users } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { SbCard, SbEmptyState, SbSection, SbSettingRow } from "./SbUIKit";

type Props = {
  asPage?: boolean;
};

type TrustedDeviceRow = {
  pubkey: string;
  host: string;
  status: string;
};

function shortDeviceLabel(pubkey: string): string {
  if (pubkey.length <= 16) return pubkey;
  return `${pubkey.slice(0, 8)}…${pubkey.slice(-6)}`;
}

export function SbPeerConnectPanel({ asPage }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [peers, setPeers] = useState<Record<string, Record<string, unknown>>>({});
  const [deviceId, setDeviceId] = useState("");
  const [blockId, setBlockId] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setPeers(await cnexusProductApi.fetchNetworkPeers());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const trustedDevices = useMemo((): TrustedDeviceRow[] => {
    return Object.entries(peers)
      .map(([pubkey, row]) => ({
        pubkey,
        host: String(row.host || ""),
        status: String(row.status || "unknown"),
      }))
      .filter((row) => row.status === "trusted" || row.status === "online")
      .sort((a, b) => a.host.localeCompare(b.host));
  }, [peers]);

  const runConnect = async () => {
    if (!deviceId.trim()) return;
    setBusy("connect");
    setMessage("");
    setError("");
    try {
      await cnexusProductApi.connectToPeer(deviceId.trim());
      setMessage(copy("shareConnectOk"));
      setDeviceId("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const runBlock = async () => {
    if (!blockId.trim()) return;
    if (!window.confirm(`${copy("shareBlockRun")}？`)) return;
    setBusy("block");
    setMessage("");
    setError("");
    try {
      await cnexusProductApi.banPeer(blockId.trim());
      setMessage(copy("shareBlockDone"));
      setBlockId("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const inputClass = "w-full border rounded-xl px-3 py-2.5 text-sm font-mono outline-none focus:ring-1";
  const inputStyle = { borderColor: t.border, backgroundColor: t.chatBg, color: t.text };

  const body = (
    <>
      <SbCard accent="blue">
        <SbSettingRow
          label={asPage ? undefined : copy("shareConnectDevice")}
          hint={asPage ? undefined : copy("shareConnectDeviceHint")}
        >
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="设备 ID（64 位十六进制）"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
          />
          <button
            type="button"
            disabled={Boolean(busy) || !deviceId.trim()}
            onClick={() => void runConnect()}
            className="mt-2 px-4 py-2 rounded-xl text-sm font-medium text-white disabled:opacity-50"
            style={{ backgroundColor: t.blue }}
          >
            {busy === "connect" ? "…" : copy("shareConnectRun")}
          </button>
        </SbSettingRow>
      </SbCard>

      <SbCard padding="sm">
        <div className="flex items-center gap-2 mb-3">
          <Users className="w-4 h-4" style={{ color: "#5eead4" }} />
          <p className="text-xs font-semibold" style={{ color: t.text }}>
            {copy("shareTrustedDevices")}
            <span className="font-normal ml-1" style={{ color: t.textMuted }}>
              ({trustedDevices.length})
            </span>
          </p>
        </div>
        {trustedDevices.length === 0 ? (
          <SbEmptyState>{copy("shareTrustedDevicesEmpty")}</SbEmptyState>
        ) : (
          <ul className="space-y-2">
            {trustedDevices.map((row) => (
              <li
                key={row.pubkey}
                className="rounded-xl border px-3 py-2.5"
                style={{ borderColor: t.border, backgroundColor: t.chatBg }}
              >
                <p className="text-xs font-medium truncate" style={{ color: t.text }}>
                  {row.host || shortDeviceLabel(row.pubkey)}
                </p>
                <p className="text-[10px] font-mono truncate mt-0.5" style={{ color: t.textMuted }}>
                  {shortDeviceLabel(row.pubkey)} · {row.status}
                </p>
              </li>
            ))}
          </ul>
        )}
      </SbCard>

      <SbCard accent="none" padding="sm">
        <div className="flex items-center gap-2 mb-2">
          <Ban className="w-4 h-4" style={{ color: t.orange }} />
          <p className="text-xs font-semibold" style={{ color: t.orange }}>
            {copy("shareBlockDevice")}
          </p>
        </div>
        <p className="text-[11px] mb-3 leading-relaxed" style={{ color: t.textMuted }}>
          {copy("shareBlockDeviceHint")}
        </p>
        <input
          className={inputClass}
          style={inputStyle}
          placeholder="要屏蔽的设备 ID"
          value={blockId}
          onChange={(e) => setBlockId(e.target.value)}
        />
        <button
          type="button"
          disabled={Boolean(busy) || !blockId.trim()}
          onClick={() => void runBlock()}
          className="mt-2 px-3 py-2 rounded-xl text-xs font-medium border disabled:opacity-50"
          style={{ borderColor: t.orange, color: t.orange }}
        >
          {busy === "block" ? "…" : copy("shareBlockRun")}
        </button>
      </SbCard>

      {(message || error) && (
        <p className="text-xs px-1" style={{ color: error ? t.orange : t.green }}>
          {error || message}
        </p>
      )}
    </>
  );

  if (asPage) {
    return <div className="space-y-3">{body}</div>;
  }

  return (
    <SbSection title={copy("shareConnectDevice")} subtitle={copy("shareConnectDeviceHint")} icon={Link2}>
      {body}
    </SbSection>
  );
}
