"use client";

import { Scale, Trophy, AlertTriangle } from "lucide-react";
import type { CounterfactualEngineResult } from "@/lib/relationshipAnalysis";
import { DYNAMICS_STATE_LABELS, DRIFT_TREND_LABELS } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard, SbSection } from "../SbUIKit";

type Props = {
  counterfactual: CounterfactualEngineResult;
};

const STATE_COLORS: Record<string, string> = {
  warm: "#5eead4",
  neutral: "#94a3b8",
  cold: "#60a5fa",
  breaking: "#f472b6",
  broken: "#ef4444",
};

const TREND_LABELS: Record<string, string> = {
  improving: DRIFT_TREND_LABELS.improving,
  stable: DRIFT_TREND_LABELS.stable,
  declining: DRIFT_TREND_LABELS.declining,
};

export function DecisionPanel({ counterfactual }: Props) {
  const t = useMindTheme();
  const { bestAction, policies } = counterfactual;

  return (
    <SbSection title="决策推荐" subtitle="反事实模拟 · 我应该做什么？" icon={Scale}>
      <div className="space-y-4">
        <SbCard accent="purple" padding="sm" className="space-y-2">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4" style={{ color: "#A78BFA" }} />
            <span className="text-xs font-semibold" style={{ color: t.text }}>
              推荐行动
            </span>
          </div>
          <p className="text-base font-semibold" style={{ color: "#A78BFA" }}>
            {bestAction.action.label}
          </p>
          <div className="flex flex-wrap gap-3 text-[11px]" style={{ color: t.textMuted }}>
            <span>策略得分 {bestAction.score.toFixed(2)}</span>
            <span>预期趋势 · {TREND_LABELS[bestAction.expectedTrend]}</span>
            <span className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" style={{ color: bestAction.outcome.riskScore > 0.5 ? "#f472b6" : t.textMuted }} />
              风险 {(bestAction.outcome.riskScore * 100).toFixed(0)}%
            </span>
          </div>
        </SbCard>

        <div>
          <p className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: t.textLight }}>
            行动对比
          </p>
          <div className="overflow-x-auto cnexus-float-scroll">
            <table className="w-full text-[11px] border-collapse min-w-[480px]">
              <thead>
                <tr style={{ color: t.textMuted }}>
                  <th className="text-left py-2 pr-3 font-medium">行动</th>
                  <th className="text-right py-2 px-2 font-medium">得分</th>
                  <th className="text-right py-2 px-2 font-medium">趋势</th>
                  <th className="text-right py-2 pl-2 font-medium">风险</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((p, i) => {
                  const isBest = i === 0;
                  return (
                    <tr
                      key={p.action.id}
                      style={{
                        color: isBest ? t.text : t.textMuted,
                        backgroundColor: isBest ? "#A78BFA10" : "transparent",
                      }}
                    >
                      <td className="py-2 pr-3">{p.action.label}</td>
                      <td className="text-right py-2 px-2 font-mono">{p.score.toFixed(2)}</td>
                      <td className="text-right py-2 px-2">{TREND_LABELS[p.expectedTrend]}</td>
                      <td className="text-right py-2 pl-2">{(p.outcome.riskScore * 100).toFixed(0)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {policies.slice(0, 4).map((p) => (
            <SbCard key={p.action.id} padding="sm" className="space-y-2">
              <p className="text-xs font-medium" style={{ color: t.text }}>
                {p.action.label}
              </p>
              {Object.entries(p.outcome.stateDistribution)
                .filter(([, v]) => v > 0.01)
                .sort((a, b) => b[1] - a[1])
                .map(([state, prob]) => (
                  <div key={state}>
                    <div className="flex justify-between text-[10px] mb-0.5">
                      <span style={{ color: t.textMuted }}>{DYNAMICS_STATE_LABELS[state as keyof typeof DYNAMICS_STATE_LABELS]}</span>
                      <span style={{ color: STATE_COLORS[state] }}>{(prob * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: t.border }}>
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${prob * 100}%`, backgroundColor: STATE_COLORS[state] }}
                      />
                    </div>
                  </div>
                ))}
            </SbCard>
          ))}
        </div>
      </div>
    </SbSection>
  );
}
