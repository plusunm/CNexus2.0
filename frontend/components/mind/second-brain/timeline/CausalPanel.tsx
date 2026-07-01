"use client";

import { useMemo, useState } from "react";
import { GitMerge, Zap } from "lucide-react";
import type { CausalEngineResult } from "@/lib/relationshipAnalysis";
import { DYNAMICS_STATE_LABELS } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard, SbSection } from "../SbUIKit";

type Props = {
  causal: CausalEngineResult;
};

function fmtTime(ts: number): string {
  try {
    return new Date(ts).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(ts);
  }
}

const TYPE_LABELS: Record<string, string> = {
  message: "消息",
  reply_delay: "回复延迟",
  initiative: "主动发起",
  silence: "沉默",
  ignore: "未回应",
  emotion_shift: "语气变化",
  intensity: "强度",
};

export function CausalPanel({ causal }: Props) {
  const t = useMindTheme();
  const [activeTransitionIdx, setActiveTransitionIdx] = useState(0);

  const explanations = causal.explanations;
  const active = explanations[activeTransitionIdx] ?? explanations[0];
  const highlightIds = useMemo(
    () => new Set(active?.causes.map((c) => c.eventId) ?? []),
    [active],
  );

  const topCauses = useMemo(() => {
    const all = explanations.flatMap((ex) =>
      ex.causes.map((c) => ({ ...c, transitionLabel: `${ex.transition.from}→${ex.transition.to}` })),
    );
    return all.sort((a, b) => b.strength - a.strength).slice(0, 5);
  }, [explanations]);

  if (explanations.length === 0) {
    return (
      <SbSection title="因果解释" subtitle="行为 → 状态变化" icon={GitMerge}>
        <SbCard padding="sm">
          <p className="text-xs" style={{ color: t.textMuted }}>
            当前时间轴未检测到阶段变迁，暂无因果链可展示。
          </p>
        </SbCard>
      </SbSection>
    );
  }

  return (
    <SbSection title="因果解释" subtitle="行为事件如何驱动关系阶段变化" icon={GitMerge}>
      <div className="space-y-4">
        <SbCard accent="purple" padding="sm" className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: t.textLight }}>
            阶段变迁
          </p>
          <div className="flex flex-wrap gap-2">
            {explanations.map((ex, i) => {
              const selected = i === activeTransitionIdx;
              return (
                <button
                  key={ex.transition.id}
                  type="button"
                  className="text-[11px] px-2.5 py-1.5 rounded-lg border transition"
                  style={{
                    borderColor: selected ? "#A78BFA" : t.border,
                    color: selected ? "#A78BFA" : t.textMuted,
                    backgroundColor: selected ? "#A78BFA18" : t.chatBg,
                  }}
                  onClick={() => setActiveTransitionIdx(i)}
                >
                  {DYNAMICS_STATE_LABELS[ex.transition.from]} → {DYNAMICS_STATE_LABELS[ex.transition.to]}
                  <span className="ml-1 opacity-70">{fmtTime(ex.transition.timestamp)}</span>
                </button>
              );
            })}
          </div>
        </SbCard>

        {active && (
          <SbCard accent="teal" padding="sm" className="space-y-3">
            <p className="text-sm leading-relaxed" style={{ color: t.text }}>
              {active.summary}
            </p>
            <div>
              <p className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: t.textLight }}>
                主要原因
              </p>
              <ul className="space-y-1.5">
                {active.causes.map((c) => (
                  <li
                    key={c.eventId}
                    className="text-xs px-2.5 py-2 rounded-lg border flex items-center justify-between gap-2"
                    style={{ borderColor: "#5eead444", backgroundColor: "#5eead40d" }}
                  >
                    <span style={{ color: t.textMuted }}>
                      <span className="font-mono text-[10px] mr-1.5" style={{ color: "#5eead4" }}>
                        {TYPE_LABELS[c.type] ?? c.type}
                      </span>
                      {c.reason}
                    </span>
                    <span className="text-[10px] shrink-0 font-medium" style={{ color: "#5eead4" }}>
                      {(c.strength * 100).toFixed(0)}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </SbCard>
        )}

        {topCauses.length > 0 && (
          <SbCard padding="sm" className="space-y-2">
            <div className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5" style={{ color: "#A78BFA" }} />
              <p className="text-xs font-medium" style={{ color: t.text }}>
                全局 Top 原因
              </p>
            </div>
            <ul className="space-y-1">
              {topCauses.map((c) => (
                <li key={`${c.eventId}-${c.transitionLabel}`} className="text-[11px]" style={{ color: t.textMuted }}>
                  {(c.strength * 100).toFixed(0)}% · {c.reason}
                </li>
              ))}
            </ul>
          </SbCard>
        )}

        <div>
          <p className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: t.textLight }}>
            事件时间线（高亮为当前变迁原因）
          </p>
          <div
            className="rounded-xl border max-h-[220px] overflow-y-auto cnexus-float-scroll"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            {causal.graph.nodes.map((node) => {
              const hit = highlightIds.has(node.id);
              return (
                <div
                  key={node.id}
                  className="text-[11px] px-3 py-2 border-b last:border-b-0 flex flex-wrap gap-x-2"
                  style={{
                    borderColor: t.border,
                    backgroundColor: hit ? "#5eead414" : "transparent",
                    color: hit ? t.text : t.textMuted,
                  }}
                >
                  <span className="font-mono text-[10px]" style={{ color: hit ? "#5eead4" : t.textLight }}>
                    {TYPE_LABELS[node.type] ?? node.type}
                  </span>
                  <span>{fmtTime(node.timestamp)}</span>
                  {node.actor && <span>@{node.actor}</span>}
                  {node.text && <span className="truncate max-w-full">{node.text}</span>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </SbSection>
  );
}
