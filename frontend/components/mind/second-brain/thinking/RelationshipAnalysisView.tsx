"use client";

import clsx from "clsx";
import { Check, X } from "lucide-react";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard } from "../SbUIKit";
import { decisionOptionRows, stateRows } from "@/lib/relationshipAnalysis/display";
import type { RelationshipAnalysis } from "@/lib/relationshipAnalysis/types/relationship";

type Props = {
  data: RelationshipAnalysis;
  className?: string;
};

export function RelationshipAnalysisView({ data, className }: Props) {
  const t = useMindTheme();
  const states = stateRows(data);
  const decisions = decisionOptionRows(data);

  return (
    <div className={clsx("space-y-4", className)}>
      <SbCard accent="teal">
        <h3 className="text-sm font-semibold mb-3" style={{ color: t.text }}>
          🧠 决策结构分析
        </h3>

        <section className="space-y-2 mb-4">
          <p className="text-xs font-medium uppercase tracking-wide" style={{ color: t.textMuted }}>
            当前状态
          </p>
          <ul className="space-y-1.5">
            {states.map((row) => (
              <li
                key={row.key}
                className="flex items-center justify-between text-sm rounded-lg px-3 py-2"
                style={{ backgroundColor: t.chatBg }}
              >
                <span style={{ color: t.textMuted }}>{row.label}</span>
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: "rgba(94,234,212,0.12)", color: "#5eead4" }}
                >
                  {row.value}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-2 mb-4">
          <p className="text-xs font-medium uppercase tracking-wide" style={{ color: t.textMuted }}>
            信号拆解
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <div
              className="rounded-xl p-3 space-y-1.5"
              style={{ backgroundColor: t.chatBg, border: `1px solid ${t.border}` }}
            >
              <p className="text-xs font-medium flex items-center gap-1" style={{ color: "#2ED47A" }}>
                <Check className="w-3.5 h-3.5" /> 正向
              </p>
              {data.signals.positive.length === 0 ? (
                <p className="text-xs" style={{ color: t.textLight }}>
                  暂无
                </p>
              ) : (
                <ul className="space-y-1">
                  {data.signals.positive.map((item) => (
                    <li key={item} className="text-xs leading-relaxed" style={{ color: t.text }}>
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div
              className="rounded-xl p-3 space-y-1.5"
              style={{ backgroundColor: t.chatBg, border: `1px solid ${t.border}` }}
            >
              <p className="text-xs font-medium flex items-center gap-1" style={{ color: "#FF4D4F" }}>
                <X className="w-3.5 h-3.5" /> 负向
              </p>
              {data.signals.negative.length === 0 ? (
                <p className="text-xs" style={{ color: t.textLight }}>
                  暂无
                </p>
              ) : (
                <ul className="space-y-1">
                  {data.signals.negative.map((item) => (
                    <li key={item} className="text-xs leading-relaxed" style={{ color: t.text }}>
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>

        <section className="space-y-2 mb-4">
          <p className="text-xs font-medium uppercase tracking-wide" style={{ color: t.textMuted }}>
            不确定性
          </p>
          <ul className="space-y-1 mb-2">
            {data.uncertainty.missingInfo.map((gap) => (
              <li key={gap} className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
                · {gap}
              </li>
            ))}
          </ul>
          <p className="text-xs leading-relaxed rounded-lg px-3 py-2" style={{ backgroundColor: t.chatBg, color: t.text }}>
            风险：{data.uncertainty.risk}
          </p>
        </section>

        <section className="space-y-2 mb-4">
          <p className="text-xs font-medium uppercase tracking-wide" style={{ color: t.textMuted }}>
            决策路径
          </p>
          <div className="grid sm:grid-cols-2 gap-2">
            {decisions.map((path) => (
              <div
                key={path.id}
                className="rounded-xl p-3"
                style={{
                  backgroundColor: path.selected ? "rgba(94,234,212,0.08)" : t.chatBg,
                  border: path.selected ? "1px solid rgba(94,234,212,0.45)" : `1px solid ${t.border}`,
                }}
              >
                <p className="text-xs font-semibold mb-1" style={{ color: path.selected ? "#5eead4" : t.text }}>
                  {path.id}
                  {path.selected ? " ✓" : ""}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
                  {path.text}
                </p>
              </div>
            ))}
          </div>
          <p className="text-xs mt-2 leading-relaxed" style={{ color: t.textMuted }}>
            推荐：<span style={{ color: "#5eead4" }}>{data.decision.recommended}</span>
            {" — "}
            {data.decision.reason}
          </p>
        </section>

        <section className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide" style={{ color: t.textMuted }}>
            推荐动作
          </p>
          <ul className="space-y-1">
            {data.actions.map((action) => (
              <li key={action} className="text-xs leading-relaxed" style={{ color: t.text }}>
                · {action}
              </li>
            ))}
          </ul>
        </section>
      </SbCard>
    </div>
  );
}
