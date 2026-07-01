"use client";

import { TrendingDown, TrendingUp, Minus, AlertTriangle, Sparkles } from "lucide-react";
import type { PredictionResult } from "@/lib/relationshipAnalysis";
import {
  DYNAMICS_STATE_LABELS,
  DRIFT_TREND_LABELS,
} from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard, SbSection } from "../SbUIKit";

type Props = {
  prediction: PredictionResult;
};

const STATE_COLORS: Record<string, string> = {
  warm: "#5eead4",
  neutral: "#94a3b8",
  cold: "#60a5fa",
  breaking: "#f472b6",
  broken: "#ef4444",
};

function TrendIcon({ trend }: { trend: PredictionResult["drift"]["trend"] }) {
  if (trend === "improving") return <TrendingUp className="w-4 h-4" style={{ color: "#5eead4" }} />;
  if (trend === "declining" || trend === "accelerating_cold") {
    return <TrendingDown className="w-4 h-4" style={{ color: "#f472b6" }} />;
  }
  return <Minus className="w-4 h-4" style={{ color: "#94a3b8" }} />;
}

export function PredictionPanel({ prediction }: Props) {
  const t = useMindTheme();
  const { statePrediction, drift, scenarios } = prediction;
  const probs = statePrediction.nextStateProbabilities;

  return (
    <SbSection title="关系预测" subtitle="基于因果信号的概率未来（7–14 天窗口）" icon={Sparkles}>
      <div className="space-y-4">
        <SbCard accent="teal" padding="sm" className="space-y-3">
          <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: t.textLight }}>
            下一阶段概率
          </p>
          <div className="space-y-2">
            {probs.map((row) => (
              <div key={row.state}>
                <div className="flex justify-between text-[11px] mb-1">
                  <span style={{ color: t.textMuted }}>{DYNAMICS_STATE_LABELS[row.state]}</span>
                  <span style={{ color: STATE_COLORS[row.state] ?? t.text }}>
                    {(row.probability * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: t.border }}>
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${row.probability * 100}%`,
                      backgroundColor: STATE_COLORS[row.state] ?? "#5eead4",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </SbCard>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <SbCard padding="sm" className="space-y-2">
            <div className="flex items-center gap-2">
              <TrendIcon trend={drift.trend} />
              <span className="text-xs font-medium" style={{ color: t.text }}>
                漂移趋势 · {DRIFT_TREND_LABELS[drift.trend]}
              </span>
            </div>
            <p className="text-[11px]" style={{ color: t.textMuted }}>
              变化速度 {(drift.velocity * 100).toFixed(0)}%
            </p>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: t.border }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${drift.velocity * 100}%`,
                  backgroundColor: drift.velocity > 0.5 ? "#f472b6" : "#5eead4",
                }}
              />
            </div>
          </SbCard>

          <SbCard padding="sm" className="space-y-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" style={{ color: drift.velocity > 0.5 ? "#f472b6" : "#94a3b8" }} />
              <span className="text-xs font-medium" style={{ color: t.text }}>
                风险窗口
              </span>
            </div>
            <p className="text-lg font-semibold" style={{ color: drift.velocity > 0.5 ? "#f472b6" : t.text }}>
              ~{drift.riskWindowDays} 天
            </p>
            <p className="text-[11px]" style={{ color: t.textMuted }}>
              {drift.velocity > 0.5
                ? "降温信号较强，建议在此窗口内采取低压力验证行动"
                : "当前漂移较缓，可持续观察并记录互动变化"}
            </p>
          </SbCard>
        </div>

        <div>
          <p className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: t.textLight }}>
            场景模拟
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {scenarios.map((sc) => (
              <SbCard key={sc.action} padding="sm" className="space-y-2">
                <p className="text-xs font-medium" style={{ color: t.text }}>
                  {sc.label}
                </p>
                <ul className="space-y-1">
                  {sc.outcomes.map((o) => (
                    <li key={o.state} className="text-[10px] flex justify-between" style={{ color: t.textMuted }}>
                      <span>{DYNAMICS_STATE_LABELS[o.state]}</span>
                      <span>{(o.probability * 100).toFixed(0)}%</span>
                    </li>
                  ))}
                </ul>
              </SbCard>
            ))}
          </div>
        </div>
      </div>
    </SbSection>
  );
}
