"use client";

import { useCallback, useRef, useState } from "react";
import { RefreshCw, Network, AlertTriangle, Moon, Scale, Brain, Play } from "lucide-react";
import { useDashboardStatus } from "@/hooks/useDashboardStatus";
import { cnexusProductApi } from "@/lib/api";
import { bi, biSection, navL } from "@/lib/spine/labels";
import type { DashboardConsensusRecent, DashboardSyncLogRow } from "@/lib/dashboardTypes";
import { useMindTheme } from "../MindUiProvider";
import { MissionTopologyGraph } from "./MissionTopologyGraph";
import { RemSleepButton } from "../RemSleepButton";
import { AwakeningPanel } from "./AwakeningPanel";
import { CognitiveAuditPanel, type CognitiveAuditFocus } from "./CognitiveAuditPanel";
import { CognitivePruningPanel } from "./CognitivePruningPanel";
import { EntropyPanel } from "./EntropyPanel";

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleTimeString();
}

function shortKey(key: string) {
  if (!key) return "—";
  if (key.startsWith("http")) {
    try {
      return new URL(key).host;
    } catch {
      return key.slice(0, 18);
    }
  }
  return key.length > 16 ? `${key.slice(0, 8)}…${key.slice(-6)}` : key;
}

function resolveSyncLogPresentation(row: DashboardSyncLogRow, t: ReturnType<typeof useMindTheme>) {
  const negStatus = row.negotiation_status;
  const err = row.error || "";
  if (err === "fork_panic") {
    return { label: "分叉警告", color: t.red, border: `${t.red}55`, bg: `${t.red}10` };
  }
  if (negStatus === "negotiated_commit" || row.merge === "negotiated_commit") {
    return { label: bi(navL.missionControlConsensusReorg), color: "#5eead4", border: "#5eead455", bg: "#5eead414" };
  }
  if (err.startsWith("negotiation") || row.negotiation_error) {
    return {
      label: bi(navL.missionControlConsensusFailed),
      color: t.orange,
      border: `${t.orange}55`,
      bg: `${t.orange}14`,
    };
  }
  if (row.aligned) {
    return { label: bi(navL.missionControlConsensusAligned), color: t.green, border: t.border, bg: t.chatBg };
  }
  return { label: "检查", color: t.orange, border: t.border, bg: t.chatBg };
}

function consensusRecentLabel(row: DashboardConsensusRecent) {
  if (row.status === "negotiated_commit") return bi(navL.missionControlConsensusReorg);
  if (row.status === "aligned") return bi(navL.missionControlConsensusAligned);
  if (row.error) return bi(navL.missionControlConsensusFailed);
  return row.phase || "协商";
}

function rowHasAuditLink(row: {
  error?: string;
  negotiation_error?: string;
  memory_conflict_count?: number;
  conflict_audit_id?: string;
}) {
  return Boolean(
    row.conflict_audit_id ||
      (row.memory_conflict_count != null && row.memory_conflict_count > 0) ||
      row.error ||
      row.negotiation_error,
  );
}

export function MissionControlLayout() {
  const t = useMindTheme();
  const auditSectionRef = useRef<HTMLElement>(null);
  const [auditFocus, setAuditFocus] = useState<CognitiveAuditFocus | undefined>();
  const [actionBusy, setActionBusy] = useState("");
  const [actionHint, setActionHint] = useState("");
  const { data, loading, error, refresh } = useDashboardStatus(true);
  const forkCount = data?.peer_summary?.fork_panic ?? 0;
  const res = data?.node?.resources;
  const rem = data?.rem;
  const consensus = data?.consensus;
  const recentNegotiations = Object.entries(consensus?.recent || {}).sort(
    (a, b) => (b[1].checked_at || 0) - (a[1].checked_at || 0),
  );
  const reputationRows = Object.entries(consensus?.reputation || {}).sort(
    (a, b) => (b[1].trust_score || 0) - (a[1].trust_score || 0),
  );
  const reorgCount = recentNegotiations.filter(([, row]) => row.status === "negotiated_commit").length;
  const consensusModeLabel =
    consensus?.mode === "conservative"
      ? bi(navL.missionControlConsensusConservative)
      : bi(navL.missionControlConsensusOptimistic);
  const resilience = data?.resilience;
  const resilienceLabel =
    resilience?.label === "fortress"
      ? bi(navL.missionControlResilienceFortress)
      : resilience?.label === "strong"
        ? bi(navL.missionControlResilienceStrong)
        : resilience?.label === "recovering"
          ? bi(navL.missionControlResilienceRecovering)
          : bi(navL.missionControlResilienceCritical);
  const remLabel = rem?.running
    ? bi(navL.missionControlRemRunning)
    : rem?.last_rem_label || bi(navL.missionControlRemNever);
  const conflictBuffer = data?.conflict?.negotiation_conflict_buffer ?? 0;

  const openAudit = useCallback((row: DashboardConsensusRecent | DashboardSyncLogRow, fallbackKey?: string) => {
    const auditId = row.conflict_audit_id;
    const peerKey =
      ("peer_pubkey" in row && row.peer_pubkey) ||
      ("peer_host" in row && row.peer_host) ||
      ("peer" in row && row.peer) ||
      fallbackKey ||
      "";
    setAuditFocus({ auditId, peerKey });
    auditSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const clearAuditFocus = useCallback(() => setAuditFocus(undefined), []);

  const runReplay = useCallback(async () => {
    setActionBusy("replay");
    setActionHint("");
    try {
      const row = await cnexusProductApi.runLogReplay(true);
      setActionHint(String(row.summary || row.message || "replay ok"));
      await refresh();
    } catch (err) {
      setActionHint(err instanceof Error ? err.message : String(err));
    } finally {
      setActionBusy("");
    }
  }, [refresh]);

  const runPeerAction = useCallback(
    async (peer: { pubkey?: string; host?: string }, action: "connect" | "sync" | "genesis") => {
      const key = peer.pubkey || peer.host || "peer";
      setActionBusy(`${action}-${key}`);
      setActionHint("");
      try {
        if (action === "connect") {
          await cnexusProductApi.connectToPeer(peer.pubkey || peer.host || "");
          setActionHint(`${bi(navL.missionControlPeerConnect)} · ${shortKey(peer.host || key)}`);
        } else {
          const row = await cnexusProductApi.forcePeerSync({
            pubkey: peer.pubkey,
            host: peer.host,
            genesis: action === "genesis",
          });
          const result = (row.result || {}) as Record<string, unknown>;
          setActionHint(
            `${action === "genesis" ? bi(navL.missionControlPeerGenesis) : bi(navL.missionControlPeerSync)} · ${String(result.status || result.message || "ok")}`,
          );
        }
        await refresh();
      } catch (err) {
        setActionHint(err instanceof Error ? err.message : String(err));
      } finally {
        setActionBusy("");
      }
    },
    [refresh],
  );

  const runReputationAction = useCallback(
    async (pubkey: string, action: "blacklist" | "restore") => {
      setActionBusy(`${action}-${pubkey}`);
      setActionHint("");
      try {
        await cnexusProductApi.updateConsensusReputation(pubkey, action);
        setActionHint(
          action === "blacklist"
            ? bi(navL.missionControlReputationBlacklist)
            : bi(navL.missionControlReputationRestore),
        );
        await refresh();
      } catch (err) {
        setActionHint(err instanceof Error ? err.message : String(err));
      } finally {
        setActionBusy("");
      }
    },
    [refresh],
  );

  return (
    <div className="space-y-4 w-full min-w-0 max-w-none">
      <header className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Network className="w-5 h-5" style={{ color: "#5eead4" }} />
            <h1 className="text-xl font-bold" style={{ color: t.text }}>
              {biSection(navL.missionControlPageTitle)}
            </h1>
            {forkCount > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
                <AlertTriangle className="w-3 h-3" />
                分叉 {forkCount}
              </span>
            )}
            {consensus?.enabled && reorgCount > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">
                <Scale className="w-3 h-3" />
                重组 {reorgCount}
              </span>
            )}
            {conflictBuffer > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">
                <Brain className="w-3 h-3" />
                {bi(navL.missionControlCognitiveAuditConflicts)} {conflictBuffer}
              </span>
            )}
          </div>
          <p className="text-sm mt-1" style={{ color: t.textMuted }}>
            {biSection(navL.missionControlPageHint)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
          style={{ borderColor: t.border, color: t.textMuted }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          {bi(navL.refresh)}
        </button>
      </header>

      {error && (
        <div
          className="rounded-lg border px-3 py-2 text-sm"
          style={{ borderColor: t.orange, color: t.orange, backgroundColor: `${t.orange}14` }}
        >
          {error}
        </div>
      )}

      {data?.replay?.needed && (
        <section
          className="rounded-xl border px-3 py-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
          style={{ borderColor: `${t.orange}55`, backgroundColor: `${t.orange}10` }}
        >
          <p className="text-xs" style={{ color: t.orange }}>
            {bi(navL.missionControlReplayDue)} · replay {data.replay.replayable_total ?? 0} entries
          </p>
          <button
            type="button"
            disabled={actionBusy === "replay"}
            onClick={() => void runReplay()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{ borderColor: t.orange, color: t.orange }}
          >
            <Play className="w-3.5 h-3.5" />
            {actionBusy === "replay" ? "…" : bi(navL.missionControlReplayRun)}
          </button>
        </section>
      )}

      {actionHint && (
        <p className="text-[11px] rounded-lg border px-2 py-1.5 truncate" style={{ borderColor: t.border, color: t.textMuted }}>
          {actionHint}
        </p>
      )}

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
        {[
          {
            label: bi(navL.missionControlUptime),
            value: data?.node?.uptime_label || "—",
            sub: data?.node?.pubkey_short || "—",
          },
          {
            label: bi(navL.missionControlResources),
            value:
              res?.available && res.cpu_percent != null
                ? `${res.cpu_percent}% · ${res.memory_percent}%`
                : "N/A",
            sub:
              res?.available && res.memory_used_mb != null
                ? `RAM ${res.memory_used_mb}/${res.memory_total_mb} MB`
                : bi(navL.missionControlPsutilHint),
          },
          {
            label: bi(navL.missionControlChain),
            value: data?.chain?.last_hash_short || data?.chain?.last_hash || "0",
            sub: `${data?.chain?.entry_count ?? 0} entries · ${data?.chain?.integrity_ok ? "OK" : "FAIL"}`,
          },
          {
            label: bi(navL.missionControlPeers),
            value: `${data?.peer_summary?.online ?? 0}/${data?.peer_summary?.total ?? 0}`,
            sub: `${bi(navL.missionControlAligned)} ${data?.peer_summary?.aligned ?? 0}`,
          },
          {
            label: bi(navL.missionControlResilience),
            value:
              resilience?.score != null ? `${Math.round(resilience.score * 100)}%` : "—",
            sub: `${resilienceLabel} · ${resilience?.full_sync_nodes ?? 0}/${resilience?.total_nodes ?? 0} · replay ${data?.replay?.needed ? "due" : "ok"}`,
          },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-xl border p-3"
            style={{ borderColor: t.border, backgroundColor: t.surface }}
          >
            <p className="text-[10px] uppercase tracking-wide" style={{ color: t.textLight }}>
              {card.label}
            </p>
            <p className="text-lg font-semibold mt-1 truncate" style={{ color: t.text }}>
              {card.value}
            </p>
            <p className="text-[11px] mt-1 truncate" style={{ color: t.textMuted }}>
              {card.sub}
            </p>
          </div>
        ))}
      </section>

      <AwakeningPanel awakening={data?.awakening} onComplete={() => void refresh()} />

      <EntropyPanel entropy={data?.entropy} />

      <section
        className="rounded-xl border p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div className="flex items-center gap-2">
          <Moon className="w-4 h-4" style={{ color: t.purple }} />
          <div>
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {bi(navL.missionControlRem)}
            </p>
            <p className="text-[11px]" style={{ color: t.textMuted }}>
              {bi(navL.missionControlRemLast)}: {remLabel}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-wrap gap-3 text-[11px]" style={{ color: t.textMuted }}>
            <span>{rem?.enabled ? "ON" : "OFF"}</span>
            <span>idle {rem?.idle_seconds ?? "—"}s</span>
            <span>pruned {rem?.total_pruned ?? 0}</span>
            <span>facts {rem?.semantic_facts ?? rem?.total_facts ?? 0}</span>
            {rem?.rem_due ? <span style={{ color: t.orange }}>due</span> : null}
          </div>
          <RemSleepButton
            compact
            disabled={Boolean(rem?.running)}
            onComplete={() => void refresh()}
          />
        </div>
      </section>

      <section
        className="rounded-xl border p-3 space-y-3"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4" style={{ color: "#5eead4" }} />
            <div>
              <p className="text-xs font-medium" style={{ color: t.text }}>
                {bi(navL.missionControlConsensus)}
              </p>
              <p className="text-[11px]" style={{ color: t.textMuted }}>
                {bi(navL.missionControlConsensusMode)}: {consensusModeLabel}
                {consensus?.enabled === false ? " · 未启用" : ""}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-[11px]" style={{ color: t.textMuted }}>
            <span>
              {bi(navL.missionControlConsensusTrust)}{" "}
              {consensus?.min_trust != null ? consensus.min_trust.toFixed(2) : "—"}
            </span>
            <span>
              {bi(navL.missionControlConsensusQuorum)}{" "}
              {consensus?.quorum_ratio != null ? `${Math.round(consensus.quorum_ratio * 100)}%` : "—"}
            </span>
            <span>
              {bi(navL.missionControlConsensusReputation)} {consensus?.reputation_peers ?? 0}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-wide" style={{ color: t.textLight }}>
              {bi(navL.missionControlConsensusRecent)}
            </p>
            <div
              className="rounded-lg border p-2 h-[140px] overflow-y-auto space-y-2 text-xs"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              {recentNegotiations.length === 0 && (
                <p style={{ color: t.textMuted }}>{bi(navL.missionControlConsensusRecentEmpty)}</p>
              )}
              {recentNegotiations.map(([key, row]) => {
                const ok = row.ok && row.status === "negotiated_commit";
                const failed = Boolean(row.error);
                const color = ok ? "#5eead4" : failed ? t.orange : t.textMuted;
                const showAudit = failed && rowHasAuditLink(row);
                return (
                  <div
                    key={key}
                    className="rounded-md border px-2 py-1.5"
                    style={{ borderColor: t.border, backgroundColor: t.surface }}
                  >
                    <div className="flex justify-between gap-2" style={{ color }}>
                      <span className="inline-flex items-center gap-1.5">
                        {consensusRecentLabel(row)}
                        {row.memory_conflict_count != null && row.memory_conflict_count > 0 && (
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded-full"
                            style={{ color: t.purple, backgroundColor: t.purpleSoft }}
                          >
                            {row.memory_conflict_count}
                          </span>
                        )}
                      </span>
                      <span>{formatTime(row.checked_at)}</span>
                    </div>
                    <p className="mt-0.5 truncate font-mono" style={{ color: t.textMuted }}>
                      {shortKey(row.peer_host || row.peer_pubkey || key)}
                    </p>
                    {(row.merged_count != null || row.message || row.error) && (
                      <p className="mt-0.5 truncate" style={{ color: t.textLight }}>
                        {row.merged_count != null ? `+${row.merged_count} entries` : ""}
                        {row.merged_count != null && (row.message || row.error) ? " · " : ""}
                        {row.message || row.error || ""}
                      </p>
                    )}
                    {showAudit && (
                      <button
                        type="button"
                        onClick={() => openAudit(row, key)}
                        className="mt-1 text-[10px] underline-offset-2 hover:underline"
                        style={{ color: t.purple }}
                      >
                        {bi(navL.missionControlCognitiveAuditView)}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-wide" style={{ color: t.textLight }}>
              {bi(navL.missionControlConsensusReputation)}
            </p>
            <div
              className="rounded-lg border p-2 h-[140px] overflow-y-auto text-xs"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              {reputationRows.length === 0 && (
                <p style={{ color: t.textMuted }}>{bi(navL.missionControlConsensusRecentEmpty)}</p>
              )}
              {reputationRows.map(([pubkey, row]) => (
                <div
                  key={pubkey}
                  className="flex items-center justify-between gap-2 py-1 border-b last:border-b-0"
                  style={{ borderColor: t.border }}
                >
                  <span className="font-mono truncate text-[10px]" style={{ color: t.textMuted }}>
                    {shortKey(pubkey)}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span style={{ color: row.blacklisted ? t.red : t.green }}>
                      {(row.trust_score ?? 0.5).toFixed(2)}
                    </span>
                    {row.blacklisted ? (
                      <button
                        type="button"
                        disabled={Boolean(actionBusy)}
                        onClick={() => void runReputationAction(pubkey, "restore")}
                        className="text-[9px] underline-offset-2 hover:underline"
                        style={{ color: t.green }}
                      >
                        {bi(navL.missionControlReputationRestore)}
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={Boolean(actionBusy)}
                        onClick={() => void runReputationAction(pubkey, "blacklist")}
                        className="text-[9px] underline-offset-2 hover:underline"
                        style={{ color: t.red }}
                      >
                        {bi(navL.missionControlReputationBlacklist)}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <CognitiveAuditPanel
        ref={auditSectionRef}
        focus={auditFocus}
        conflictMeta={data?.conflict}
        onFocusHandled={clearAuditFocus}
        onSettingsChanged={() => void refresh()}
      />

      <CognitivePruningPanel pruning={data?.pruning} onComplete={() => void refresh()} />

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 space-y-2">
          <h2 className="text-sm font-medium" style={{ color: t.text }}>
            {bi(navL.missionControlTopology)}
          </h2>
          <MissionTopologyGraph
            topology={data?.topology}
            peers={data?.peers}
            localLabel={data?.node?.pubkey_short || "本节点"}
          />
        </div>
        <div className="space-y-2">
          <h2 className="text-sm font-medium" style={{ color: t.text }}>
            {bi(navL.missionControlSyncLog)}
          </h2>
          <div
            className="rounded-xl border p-3 h-[332px] overflow-y-auto space-y-2 text-xs"
            style={{ borderColor: t.border, backgroundColor: t.surface }}
          >
            {(data?.sync_log || []).length === 0 && (
              <p style={{ color: t.textMuted }}>{bi(navL.missionControlSyncEmpty)}</p>
            )}
            {(data?.sync_log || []).map((row, index) => {
              const presentation = resolveSyncLogPresentation(row, t);
              const showAudit =
                (presentation.label === bi(navL.missionControlConsensusFailed) ||
                  Boolean(row.negotiation_error)) &&
                rowHasAuditLink(row);
              return (
                <div
                  key={`${row.peer}-${index}`}
                  className="rounded-lg border p-2"
                  style={{
                    borderColor: presentation.border,
                    backgroundColor: presentation.bg,
                  }}
                >
                  <div className="flex justify-between" style={{ color: presentation.color }}>
                    <span className="inline-flex items-center gap-1.5">
                      {presentation.label}
                      {row.memory_conflict_count != null && row.memory_conflict_count > 0 && (
                        <span
                          className="text-[9px] px-1.5 py-0.5 rounded-full"
                          style={{ color: t.purple, backgroundColor: t.purpleSoft }}
                        >
                          {row.memory_conflict_count}
                        </span>
                      )}
                    </span>
                    <span>{formatTime(row.at)}</span>
                  </div>
                  <p className="mt-1 truncate" style={{ color: t.textMuted }}>
                    {row.peer}
                  </p>
                  {(row.merged_count != null || row.message || row.negotiation_error) && (
                    <p className="mt-0.5 truncate text-[10px]" style={{ color: t.textLight }}>
                      {row.merged_count != null ? `merged ${row.merged_count}` : ""}
                      {row.merged_count != null && (row.message || row.negotiation_error) ? " · " : ""}
                      {row.message || row.negotiation_error || ""}
                    </p>
                  )}
                  {showAudit && (
                    <button
                      type="button"
                      onClick={() => openAudit(row, row.peer)}
                      className="mt-1 text-[10px] underline-offset-2 hover:underline"
                      style={{ color: t.purple }}
                    >
                      {bi(navL.missionControlCognitiveAuditView)}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="rounded-xl border overflow-hidden" style={{ borderColor: t.border }}>
        <div className="px-3 py-2 border-b" style={{ borderColor: t.border, backgroundColor: t.surface }}>
          <h2 className="text-sm font-medium" style={{ color: t.text }}>
            {bi(navL.missionControlPeerMap)}
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase" style={{ color: t.textLight }}>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2">Host</th>
                <th className="px-3 py-2">Pubkey</th>
                <th className="px-3 py-2">延迟</th>
                <th className="px-3 py-2">对齐</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {(data?.peers || []).map((peer) => {
                const busyKey = peer.pubkey || peer.host || "";
                return (
                <tr key={peer.pubkey} className="border-t" style={{ borderColor: t.border }}>
                  <td className="px-3 py-2">
                    <span
                      style={{
                        color:
                          peer.fork_panic ? t.red : peer.status === "online" ? t.green : t.textMuted,
                      }}
                    >
                      {peer.fork_panic ? "分叉" : peer.status === "online" ? "在线" : "离线"}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs" style={{ color: t.blue }}>
                    {peer.host || "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs" style={{ color: t.textMuted }}>
                    {peer.pubkey_short || "—"}
                  </td>
                  <td className="px-3 py-2">{peer.latency_ms != null ? `${peer.latency_ms} ms` : "—"}</td>
                  <td className="px-3 py-2" style={{ color: peer.aligned ? t.green : t.orange }}>
                    {peer.aligned ? "是" : "否"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1.5 text-[10px]">
                      <button
                        type="button"
                        disabled={Boolean(actionBusy)}
                        onClick={() => void runPeerAction(peer, "connect")}
                        className="underline-offset-2 hover:underline"
                        style={{ color: t.blue }}
                      >
                        {bi(navL.missionControlPeerConnect)}
                      </button>
                      <button
                        type="button"
                        disabled={Boolean(actionBusy)}
                        onClick={() => void runPeerAction(peer, "sync")}
                        className="underline-offset-2 hover:underline"
                        style={{ color: t.textMuted }}
                      >
                        {bi(navL.missionControlPeerSync)}
                      </button>
                      <button
                        type="button"
                        disabled={Boolean(actionBusy)}
                        onClick={() => void runPeerAction(peer, "genesis")}
                        className="underline-offset-2 hover:underline"
                        style={{ color: t.purple }}
                      >
                        {bi(navL.missionControlPeerGenesis)}
                      </button>
                    </div>
                  </td>
                </tr>
              );
              })}
            </tbody>
          </table>
          {(data?.peers || []).length === 0 && (
            <p className="text-center py-8 text-sm" style={{ color: t.textMuted }}>
              {bi(navL.missionControlPeersEmpty)}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
