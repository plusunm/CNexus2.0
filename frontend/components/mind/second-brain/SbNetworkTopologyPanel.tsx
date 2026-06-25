"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, Network, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { cnexusProductApi } from "@/lib/api";
import { useCognitiveCopy, buildLabShellHref } from "@/lib/cognitive";
import { useDashboardStatus } from "@/hooks/useDashboardStatus";
import { useMindTheme } from "../MindUiProvider";
import { MissionTopologyGraph } from "../home/MissionTopologyGraph";
import { SbCard, SbSection, SbStat } from "./SbUIKit";

type Props = {
  asPage?: boolean;
};

export function SbNetworkTopologyPanel({ asPage }: Props) {
  const t = useMindTheme();
  const router = useRouter();
  const { t: copy } = useCognitiveCopy();
  const { data, loading, refresh } = useDashboardStatus();
  const [dhtNodes, setDhtNodes] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const deviceId = data?.node?.pubkey || data?.topology?.nodes?.[0]?.id || "";
  const shortId = data?.node?.pubkey_short || "—";

  const loadDht = useCallback(async () => {
    try {
      const row = await cnexusProductApi.fetchDhtStatus();
      setDhtNodes(typeof row.node_count === "number" ? row.node_count : null);
    } catch {
      setDhtNodes(null);
    }
  }, []);

  useEffect(() => {
    void loadDht();
  }, [loadDht]);

  const refreshAll = async () => {
    setBusy(true);
    try {
      await Promise.all([refresh(), loadDht()]);
    } finally {
      setBusy(false);
    }
  };

  const copyDeviceId = async () => {
    if (!deviceId) return;
    try {
      await navigator.clipboard.writeText(deviceId);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const openLab = () => {
    router.push(buildLabShellHref({ view: "network", from: "second-brain-explain" }));
  };

  const refreshButton = (
    <button
      type="button"
      disabled={busy || loading}
      onClick={() => void refreshAll()}
      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs border disabled:opacity-50"
      style={{ borderColor: t.border, color: t.textMuted }}
    >
      <RefreshCw className={`w-3.5 h-3.5 ${busy || loading ? "animate-spin" : ""}`} />
      {copy("refresh")}
    </button>
  );

  const body = (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <SbStat
          label={copy("shareDevicesOnline")}
          value={data?.peer_summary?.online ?? 0}
          tone="teal"
        />
        <SbStat
          label={copy("shareDevicesSynced")}
          value={data?.peer_summary?.aligned ?? 0}
          tone="purple"
        />
        <SbStat
          label={copy("shareDiscoveryReach")}
          value={dhtNodes ?? "—"}
          hint={shortId !== "—" ? `本机 ${shortId}` : undefined}
        />
      </div>

      <SbCard accent="teal" padding="sm">
        <MissionTopologyGraph
          topology={data?.topology}
          peers={data?.peers}
          localLabel={shortId}
        />
      </SbCard>

      <SbCard padding="sm">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {copy("shareMyDeviceId")}
            </p>
            <p
              className="text-[11px] mt-1 font-mono truncate"
              style={{ color: t.textMuted }}
              title={deviceId || undefined}
            >
              {deviceId || "—"}
            </p>
          </div>
          <button
            type="button"
            disabled={!deviceId}
            onClick={() => void copyDeviceId()}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border disabled:opacity-50 shrink-0"
            style={{ borderColor: t.border, color: copied ? "#5eead4" : t.textMuted }}
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? copy("shareCopied") : copy("shareCopyDeviceId")}
          </button>
        </div>
        <button
          type="button"
          onClick={openLab}
          className="mt-3 text-[11px] underline-offset-2 hover:underline"
          style={{ color: t.textLight }}
        >
          {copy("shareOpenLabLink")}
        </button>
      </SbCard>
    </>
  );

  if (asPage) {
    return (
      <div className="space-y-3">
        <div className="flex justify-end">{refreshButton}</div>
        {body}
      </div>
    );
  }

  return (
    <SbSection
      title={copy("shareMyNetwork")}
      subtitle={copy("shareMyNetworkHint")}
      icon={Network}
      action={refreshButton}
    >
      {body}
    </SbSection>
  );
}
