"use client";

import { forwardRef, useCallback, useEffect, useMemo, useState } from "react";
import { Brain, MessageSquare, RefreshCw } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { conflictChatWorkbenchHref, saveConflictChatSeed } from "@/lib/conflictChatBridge";
import { useCognitiveCopy } from "@/lib/cognitive";
import { bi, navL } from "@/lib/spine/labels";
import type { DashboardStatus } from "@/lib/dashboardTypes";
import { useMindTheme } from "../MindUiProvider";

type AuditPair = {
  block_id?: string;
  local?: { content?: string; label?: string };
  remote?: { content?: string; label?: string; source_peer?: string };
  resolution?: {
    status?: string;
    merged_content?: string;
    fork?: { local?: string; remote?: string; label?: string };
    rationale?: string;
    source?: string;
    temperature?: number;
    global_entropy?: string;
    error?: string;
  };
};

type AuditItem = {
  id?: string;
  at?: number;
  peer_pubkey?: string;
  peer_host?: string;
  negotiation_error?: string;
  negotiation_message?: string;
  global_entropy?: string;
  conflict_count?: number;
  resolved_count?: number;
  llm_used?: boolean;
  pairs?: AuditPair[];
};

export type CognitiveAuditFocus = {
  auditId?: string;
  peerKey?: string;
};

type CognitiveAuditPanelProps = {
  focus?: CognitiveAuditFocus;
  conflictMeta?: DashboardStatus["conflict"];
  onFocusHandled?: () => void;
  onSettingsChanged?: () => void;
};

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
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
  return key.length > 18 ? `${key.slice(0, 8)}…${key.slice(-6)}` : key;
}

function normalizePeerKey(value?: string) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return "";
  if (text.startsWith("http://") || text.startsWith("https://")) {
    try {
      return new URL(text).host.toLowerCase();
    } catch {
      return text;
    }
  }
  return text;
}

function itemMatchesPeer(item: AuditItem, peerKey?: string) {
  const needle = normalizePeerKey(peerKey);
  if (!needle) return false;
  const candidates = [item.peer_pubkey, item.peer_host].map(normalizePeerKey).filter(Boolean);
  return candidates.some((candidate) => candidate === needle || candidate.includes(needle) || needle.includes(candidate));
}

function statusLabel(status?: string) {
  if (status === "merged") return bi(navL.missionControlCognitiveAuditMerged);
  if (status === "forked") return bi(navL.missionControlCognitiveAuditForked);
  return status || "—";
}

function statusColor(status: string | undefined, t: ReturnType<typeof useMindTheme>) {
  if (status === "merged") return t.green;
  if (status === "forked") return t.purple;
  if (status === "aligned") return t.blue;
  return t.orange;
}

function synthesisText(pair: AuditPair) {
  const res = pair.resolution;
  if (!res) return "";
  if (res.status === "merged") return res.merged_content || "";
  if (res.status === "forked") {
    return `A: ${res.fork?.local || "—"}\nB: ${res.fork?.remote || "—"}`;
  }
  return res.rationale || "";
}

export const CognitiveAuditPanel = forwardRef<HTMLElement, CognitiveAuditPanelProps>(
  function CognitiveAuditPanel({ focus, conflictMeta, onFocusHandled, onSettingsChanged }, ref) {
    const t = useMindTheme();
    const { t: copy } = useCognitiveCopy();
    const [loading, setLoading] = useState(false);
    const [settingsBusy, setSettingsBusy] = useState(false);
    const [pairBusy, setPairBusy] = useState("");
    const [error, setError] = useState("");
    const [items, setItems] = useState<AuditItem[]>([]);
    const [meta, setMeta] = useState<{ llm_auto_resolve?: boolean; count?: number }>({});
    const [autoResolve, setAutoResolve] = useState(Boolean(conflictMeta?.negotiation_conflict_enabled ?? true));
    const [selectedId, setSelectedId] = useState<string>("");

    const load = useCallback(async () => {
      setLoading(true);
      setError("");
      try {
        const row = await cnexusProductApi.fetchNegotiationConflicts();
        const nextItems = (row.items || []) as AuditItem[];
        setItems(nextItems);
        setMeta({ llm_auto_resolve: row.llm_auto_resolve, count: row.count });
        setAutoResolve(row.enabled ?? true);
        setSelectedId((prev) => {
          if (prev && nextItems.some((item) => item.id === prev)) return prev;
          return nextItems[0]?.id || "";
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }, []);

    useEffect(() => {
      void load();
    }, [load]);

    useEffect(() => {
      if (conflictMeta?.negotiation_conflict_enabled != null) {
        setAutoResolve(conflictMeta.negotiation_conflict_enabled);
      }
    }, [conflictMeta?.negotiation_conflict_enabled]);

    useEffect(() => {
      if (!focus?.auditId && !focus?.peerKey) return;
      if (items.length === 0) return;
      const byId = focus.auditId ? items.find((item) => item.id === focus.auditId) : undefined;
      const byPeer = !byId && focus.peerKey ? items.find((item) => itemMatchesPeer(item, focus.peerKey)) : undefined;
      const target = byId || byPeer;
      if (target?.id) {
        setSelectedId(target.id);
        onFocusHandled?.();
      }
    }, [focus, items, onFocusHandled]);

    const selected = useMemo(
      () => items.find((item) => item.id === selectedId) || items[0],
      [items, selectedId],
    );

    const updateSettings = async (patch: { llmAutoResolve?: boolean; autoResolveEnabled?: boolean }) => {
      setSettingsBusy(true);
      setError("");
      try {
        const row = await cnexusProductApi.updateConflictSettings(patch);
        if (row.llm_auto_resolve != null) {
          setMeta((prev) => ({ ...prev, llm_auto_resolve: row.llm_auto_resolve }));
        }
        if (row.auto_resolve_enabled != null) setAutoResolve(row.auto_resolve_enabled);
        onSettingsChanged?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setSettingsBusy(false);
      }
    };

    const runPairAction = async (
      pairKey: string,
      pair: AuditPair,
      action: "apply" | "resolve",
      item: AuditItem,
    ) => {
      setPairBusy(pairKey);
      setError("");
      try {
        const report = await cnexusProductApi.resolveConflictPair({
          block_id: pair.block_id,
          local: pair.local || {},
          remote: pair.remote || {},
          apply: action === "apply",
          use_llm: meta.llm_auto_resolve ?? true,
          mode: "emergent",
        });
        setItems((prev) =>
          prev.map((row) => {
            if (row.id !== item.id) return row;
            const pairs = (row.pairs || []).map((p) =>
              p.block_id === pair.block_id
                ? {
                    ...p,
                    resolution: {
                      status: String(report.status || ""),
                      merged_content: report.merged_content as string | undefined,
                      fork: report.fork as AuditPair["resolution"] extends { fork?: infer F } ? F : never,
                      rationale: report.rationale as string | undefined,
                      source: report.source as string | undefined,
                      temperature: report.temperature as number | undefined,
                      global_entropy: report.global_entropy as string | undefined,
                    },
                  }
                : p,
            );
            return { ...row, pairs };
          }),
        );
        onSettingsChanged?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setPairBusy("");
      }
    };

    const discussPair = (pair: AuditPair, item: AuditItem) => {
      saveConflictChatSeed({
        blockId: pair.block_id,
        local: pair.local?.content,
        remote: pair.remote?.content,
        synthesis: synthesisText(pair),
        status: pair.resolution?.status,
        peerLabel: shortKey(item.peer_host || item.peer_pubkey || ""),
      });
      if (typeof window !== "undefined") {
        window.location.href = conflictChatWorkbenchHref();
      }
    };

    return (
      <section
        ref={ref}
        className="rounded-xl border p-3 space-y-3"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="flex items-start gap-2">
            <Brain className="w-4 h-4 mt-0.5" style={{ color: t.purple }} />
            <div>
              <p className="text-xs font-medium" style={{ color: t.text }}>
                {copy("conflictResolution")}
              </p>
              <p className="text-[11px] mt-0.5" style={{ color: t.textMuted }}>
                {copy("conflictLocalView")} · {copy("conflictRemoteView")} · {copy("conflictSynthesis")}
              </p>
              <p className="text-[10px] mt-1" style={{ color: t.textLight }}>
                {autoResolve ? "auto ON" : "auto OFF"} · buffer {meta.count ?? 0}
                {meta.llm_auto_resolve ? " · LLM" : " · heuristic"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void updateSettings({ autoResolveEnabled: !autoResolve })}
              disabled={settingsBusy || loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
              style={{
                borderColor: autoResolve ? t.green : t.border,
                color: autoResolve ? t.green : t.textMuted,
                backgroundColor: autoResolve ? `${t.green}14` : "transparent",
              }}
            >
              {bi(navL.missionControlAutoConflict)}
            </button>
            <button
              type="button"
              onClick={() => void updateSettings({ llmAutoResolve: !(meta.llm_auto_resolve ?? false) })}
              disabled={settingsBusy || loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
              style={{
                borderColor: meta.llm_auto_resolve ? t.purple : t.border,
                color: meta.llm_auto_resolve ? t.purple : t.textMuted,
                backgroundColor: meta.llm_auto_resolve ? t.purpleSoft : "transparent",
              }}
            >
              {meta.llm_auto_resolve
                ? bi(navL.missionControlCognitiveAuditLlmAuto)
                : bi(navL.missionControlCognitiveAuditLlmHeuristic)}
            </button>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              {copy("refresh")}
            </button>
          </div>
        </div>

        {error && (
          <p className="text-[11px] rounded-lg border px-2 py-1.5" style={{ borderColor: t.orange, color: t.orange }}>
            {error}
          </p>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 min-h-[280px]">
          <div
            className="lg:col-span-2 rounded-lg border p-2 space-y-1.5 overflow-y-auto max-h-[360px]"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            {items.length === 0 && (
              <p className="text-[11px] p-2" style={{ color: t.textMuted }}>
                {bi(navL.missionControlCognitiveAuditEmpty)}
              </p>
            )}
            {items.map((item) => {
              const active = (selected?.id || "") === item.id;
              const pairCount = item.pairs?.length ?? item.resolved_count ?? 0;
              return (
                <button
                  key={item.id || String(item.at)}
                  type="button"
                  onClick={() => setSelectedId(item.id || "")}
                  className="w-full text-left rounded-md border px-2 py-1.5 transition-colors"
                  style={{
                    borderColor: active ? t.purple : t.border,
                    backgroundColor: active ? t.purpleSoft : t.surface,
                  }}
                >
                  <div className="flex justify-between gap-2 text-[11px]">
                    <span style={{ color: t.orange }}>{item.negotiation_error || "conflict"}</span>
                    <span style={{ color: t.textLight }}>{formatTime(item.at)}</span>
                  </div>
                  <p className="font-mono text-[10px] truncate mt-0.5" style={{ color: t.textMuted }}>
                    {shortKey(item.peer_host || item.peer_pubkey || "")}
                  </p>
                  <p className="text-[10px] mt-0.5" style={{ color: t.textLight }}>
                    {pairCount} pair(s) · resolved {item.resolved_count ?? 0}/{item.conflict_count ?? pairCount}
                  </p>
                </button>
              );
            })}
          </div>

          <div
            className="lg:col-span-3 rounded-lg border p-3 space-y-3 overflow-y-auto max-h-[360px]"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            {!selected && (
              <p className="text-[11px]" style={{ color: t.textMuted }}>
                {bi(navL.missionControlCognitiveAuditEmpty)}
              </p>
            )}
            {selected &&
              (selected.pairs || []).map((pair, index) => {
                const res = pair.resolution;
                const color = statusColor(res?.status, t);
                const pairKey = `${selected.id}-${pair.block_id || index}`;
                const busy = pairBusy === pairKey;
                return (
                  <div
                    key={pairKey}
                    className="rounded-lg border p-2 space-y-2"
                    style={{ borderColor: t.border, backgroundColor: t.surface }}
                  >
                    <p className="font-mono text-[10px]" style={{ color: t.blue }}>
                      {pair.block_id?.slice(0, 24) || "block"}
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <div className="rounded-md border p-2" style={{ borderColor: t.border }}>
                        <p className="text-[10px] uppercase mb-1" style={{ color: t.textLight }}>
                          {bi(navL.missionControlCognitiveAuditLocal)}
                        </p>
                        <p className="text-[11px] whitespace-pre-wrap break-words" style={{ color: t.text }}>
                          {pair.local?.content || "—"}
                        </p>
                      </div>
                      <div className="rounded-md border p-2" style={{ borderColor: t.border }}>
                        <p className="text-[10px] uppercase mb-1" style={{ color: t.textLight }}>
                          {bi(navL.missionControlCognitiveAuditRemote)}
                        </p>
                        <p className="text-[11px] whitespace-pre-wrap break-words" style={{ color: t.text }}>
                          {pair.remote?.content || "—"}
                        </p>
                      </div>
                    </div>
                    <div
                      className="rounded-md border p-2"
                      style={{ borderColor: `${color}55`, backgroundColor: `${color}10` }}
                    >
                      <p className="text-[10px] uppercase mb-1" style={{ color }}>
                        {bi(navL.missionControlCognitiveAuditSynthesis)} · {statusLabel(res?.status)}
                        {res?.source ? ` · ${res.source}` : ""}
                        {res?.temperature != null ? ` · T=${res.temperature}` : ""}
                      </p>
                      {res?.error && (
                        <p className="text-[11px]" style={{ color: t.orange }}>
                          {res.error}
                        </p>
                      )}
                      {res?.status === "merged" && (
                        <p className="text-[11px] whitespace-pre-wrap break-words" style={{ color: t.text }}>
                          {res.merged_content || "—"}
                        </p>
                      )}
                      {res?.status === "forked" && (
                        <div className="text-[11px] space-y-1" style={{ color: t.text }}>
                          <p>A: {res.fork?.local || "—"}</p>
                          <p>B: {res.fork?.remote || "—"}</p>
                        </div>
                      )}
                      {res?.rationale && (
                        <p className="text-[10px] mt-1" style={{ color: t.textMuted }}>
                          {res.rationale}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void runPairAction(pairKey, pair, "apply", selected)}
                        className="text-[10px] px-2 py-1 rounded border disabled:opacity-50"
                        style={{ borderColor: t.green, color: t.green }}
                      >
                        {busy ? "…" : bi(navL.missionControlAuditApply)}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void runPairAction(pairKey, pair, "resolve", selected)}
                        className="text-[10px] px-2 py-1 rounded border disabled:opacity-50"
                        style={{ borderColor: t.border, color: t.textMuted }}
                      >
                        {bi(navL.missionControlAuditResolve)}
                      </button>
                      <button
                        type="button"
                        onClick={() => discussPair(pair, selected)}
                        className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded border"
                        style={{ borderColor: t.purple, color: t.purple }}
                      >
                        <MessageSquare className="w-3 h-3" />
                        {bi(navL.missionControlAuditDiscuss)}
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </section>
    );
  },
);
