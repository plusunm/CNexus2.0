"use client";

import type { RelationshipAnalysis, RelationshipTimeline } from "@/lib/relationshipAnalysis";
import { DYNAMICS_STATE_LABELS, stateRows } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard } from "../SbUIKit";
import { PhaseIndicator } from "./PhaseIndicator";

type Props = {
  timeline: RelationshipTimeline;
  analysis: RelationshipAnalysis;
};

export function StateSnapshotCard({ timeline, analysis }: Props) {
  const t = useMindTheme();
  const rows = stateRows(analysis);

  return (
    <SbCard accent="purple" className="space-y-4">
      <PhaseIndicator current={timeline.currentState} />
      <div>
        <p className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: t.textLight }}>
          当前快照
        </p>
        <p className="text-lg font-semibold" style={{ color: t.text }}>
          {DYNAMICS_STATE_LABELS[timeline.currentState]}
        </p>
        <p className="text-xs mt-1 leading-relaxed" style={{ color: t.textMuted }}>
          {analysis.decision.reason}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {rows.map((row) => (
          <div
            key={row.key}
            className="text-xs px-2.5 py-2 rounded-lg border"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <span className="block text-[10px] mb-0.5" style={{ color: t.textLight }}>
              {row.label}
            </span>
            <span style={{ color: t.text }}>{row.value}</span>
          </div>
        ))}
      </div>
      {timeline.stateHistory.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wider font-medium mb-1.5" style={{ color: t.textLight }}>
            阶段变迁
          </p>
          <ul className="space-y-1">
            {timeline.stateHistory.map((h, i) => (
              <li key={`${h.segmentIndex}-${i}`} className="text-[11px]" style={{ color: t.textMuted }}>
                段 {h.segmentIndex + 1}：{DYNAMICS_STATE_LABELS[h.from]} → {DYNAMICS_STATE_LABELS[h.to]}
              </li>
            ))}
          </ul>
        </div>
      )}
    </SbCard>
  );
}
