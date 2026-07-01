"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Layers, Zap, AlertTriangle, Rocket, Tag } from "lucide-react";
import type { DecisionModelCard, RelationshipAnalysisCard } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard } from "../SbUIKit";
import { RelationshipPhaseMap } from "./RelationshipPhaseMap";
import { RelationshipAnalysisView } from "./RelationshipAnalysisView";
import { RELATIONSHIP_DECISION_LIBRARY } from "@/lib/relationshipAnalysis/library/relationshipDecisionLibrary";
import type { RelationshipLibraryModelId } from "@/lib/relationshipAnalysis/library/relationshipDecisionLibrary";

type Props = {
  card: DecisionModelCard;
  analysis?: RelationshipAnalysisCard;
};

function SignalList({ label, items, tone }: { label: string; items: string[]; tone: "positive" | "negative" }) {
  const t = useMindTheme();
  const color = tone === "positive" ? "#5eead4" : "#f472b6";
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider font-medium mb-1.5" style={{ color: t.textLight }}>
        {label}
      </p>
      <ul className="space-y-1">
        {items.map((row) => (
          <li
            key={row}
            className="text-xs px-2 py-1.5 rounded-lg border"
            style={{ borderColor: `${color}33`, color: t.textMuted, backgroundColor: `${color}0d` }}
          >
            {row}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DecisionModelCardView({ card, analysis }: Props) {
  const t = useMindTheme();
  const [showAnalysis, setShowAnalysis] = useState(false);

  return (
    <div className="space-y-4">
      <SbCard accent="purple" className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 shrink-0" style={{ color: "#A78BFA" }} />
              <h3 className="text-base font-semibold" style={{ color: t.text }}>
                {card.title}
              </h3>
            </div>
            <span
              className="inline-block text-[10px] px-2 py-0.5 rounded-full border"
              style={{ borderColor: "#A78BFA55", color: "#A78BFA", backgroundColor: "#A78BFA14" }}
            >
              {card.problemType}
            </span>
          </div>
          <RelationshipPhaseMap activeId={card.libraryModelId} className="mt-2" />
          {card.reusabilityTags.length > 0 && (
            <div className="flex flex-wrap gap-1 max-w-[220px] justify-end">
              {card.reusabilityTags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                  style={{ color: t.textMuted, backgroundColor: t.chatBg }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <p className="text-sm leading-relaxed" style={{ color: t.text }}>
          {card.modelSummary}
        </p>
      </SbCard>

      <SbCard className="space-y-3">
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5" style={{ color: "#5eead4" }} />
          <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: t.textLight }}>
            信号模型
          </h4>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <SignalList label="正向信号" items={card.signalModel.keyPositiveSignals} tone="positive" />
          <SignalList label="负向信号" items={card.signalModel.keyNegativeSignals} tone="negative" />
        </div>
      </SbCard>

      <SbCard className="space-y-3">
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5" style={{ color: "#60a5fa" }} />
          <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: t.textLight }}>
            决策模型
          </h4>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider font-medium mb-1.5" style={{ color: t.textLight }}>
            触发条件
          </p>
          <ul className="space-y-1">
            {card.decisionModel.triggerConditions.map((row) => (
              <li key={row} className="text-xs flex items-start gap-1.5" style={{ color: t.textMuted }}>
                <span style={{ color: "#60a5fa" }}>▸</span>
                {row}
              </li>
            ))}
          </ul>
        </div>
        <div
          className="text-xs px-3 py-2 rounded-lg border font-mono leading-relaxed whitespace-pre-wrap"
          style={{ borderColor: "#60a5fa33", color: t.text, backgroundColor: "#60a5fa0d" }}
        >
          {card.decisionModel.recommendedActionLogic}
        </div>
        {card.libraryModelId && (
          <details className="text-[11px]" style={{ color: t.textMuted }}>
            <summary className="cursor-pointer select-none opacity-80 hover:opacity-100">
              查看完整决策分支
            </summary>
            <pre className="mt-2 whitespace-pre-wrap font-sans leading-relaxed opacity-90">
              {card.libraryModelId &&
              RELATIONSHIP_DECISION_LIBRARY[card.libraryModelId as RelationshipLibraryModelId]
                ?.decisionLogic}
            </pre>
          </details>
        )}
      </SbCard>

      <SbCard className="space-y-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5" style={{ color: "#fbbf24" }} />
          <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: t.textLight }}>
            风险模型
          </h4>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="text-[10px] uppercase tracking-wider font-medium mb-1.5" style={{ color: t.textLight }}>
              核心风险
            </p>
            <ul className="space-y-1">
              {card.riskModel.coreRisks.map((row) => (
                <li key={row} className="text-xs" style={{ color: t.textMuted }}>
                  {row}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider font-medium mb-1.5" style={{ color: t.textLight }}>
              误判来源
            </p>
            <ul className="space-y-1">
              {card.riskModel.misjudgmentSources.map((row) => (
                <li key={row} className="text-xs" style={{ color: t.textMuted }}>
                  {row}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </SbCard>

      <SbCard className="space-y-3">
        <div className="flex items-center gap-2">
          <Rocket className="w-3.5 h-3.5" style={{ color: "#5eead4" }} />
          <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: t.textLight }}>
            行动模板
          </h4>
        </div>
        <ol className="space-y-2">
          {card.actionTemplate.map((row, idx) => (
            <li
              key={row}
              className="text-xs flex gap-2 px-2.5 py-2 rounded-lg border"
              style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.chatBg }}
            >
              <span className="font-mono shrink-0" style={{ color: "#5eead4" }}>
                {idx + 1}.
              </span>
              {row}
            </li>
          ))}
        </ol>
      </SbCard>

      {card.reusabilityTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <Tag className="w-3 h-3" style={{ color: t.textLight }} />
          {card.reusabilityTags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-2 py-0.5 rounded-full border font-mono"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {analysis && (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: t.border }}>
          <button
            type="button"
            className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left"
            onClick={() => setShowAnalysis((v) => !v)}
            aria-expanded={showAnalysis}
          >
            <span className="text-xs font-medium" style={{ color: t.textMuted }}>
              原始分析快照
            </span>
            {showAnalysis ? (
              <ChevronUp className="w-4 h-4" style={{ color: t.textMuted }} />
            ) : (
              <ChevronDown className="w-4 h-4" style={{ color: t.textMuted }} />
            )}
          </button>
          {showAnalysis && (
            <div className="px-3 pb-3 border-t" style={{ borderColor: t.border }}>
              <RelationshipAnalysisView data={analysis} className="mt-3" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
