/**
 * Presentation layer — maps canonical enums to human-readable labels.
 * UI may import from here; adapter must NOT.
 */

import type {
  DecisionOptionId,
  LevelBand,
  RelationshipAnalysis,
  RelationshipAnalysisState,
  RelationshipStage,
} from "./types/relationship";
import type { RelationshipDynamicsState } from "./timeline/timelineSchema";

export const DYNAMICS_STATE_LABELS: Record<RelationshipDynamicsState, string> = {
  warm: "升温",
  neutral: "平稳",
  cold: "冷淡",
  breaking: "崩解中",
  broken: "已断裂",
};

export const DYNAMICS_STATE_ORDER: RelationshipDynamicsState[] = [
  "warm",
  "neutral",
  "cold",
  "breaking",
  "broken",
];

export const LEVEL_BAND_LABELS: Record<LevelBand, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

export const RELATIONSHIP_STAGE_LABELS: Record<RelationshipStage, string> = {
  stable: "平稳",
  cold: "降温",
  uncertain: "不确定",
  broken: "高风险",
};

export const STATE_FIELD_LABELS: Record<keyof RelationshipAnalysisState, string> = {
  emotionConnection: "投入与连接",
  initiativeLevel: "主动性",
  interactionFrequency: "互动频率",
  relationshipStage: "局面阶段",
};

export function stateRows(analysis: RelationshipAnalysis): Array<{ key: string; label: string; value: string }> {
  const { state } = analysis;
  return [
    { key: "emotionConnection", label: STATE_FIELD_LABELS.emotionConnection, value: LEVEL_BAND_LABELS[state.emotionConnection] },
    { key: "initiativeLevel", label: STATE_FIELD_LABELS.initiativeLevel, value: LEVEL_BAND_LABELS[state.initiativeLevel] },
    {
      key: "interactionFrequency",
      label: STATE_FIELD_LABELS.interactionFrequency,
      value: LEVEL_BAND_LABELS[state.interactionFrequency],
    },
    {
      key: "relationshipStage",
      label: STATE_FIELD_LABELS.relationshipStage,
      value: RELATIONSHIP_STAGE_LABELS[state.relationshipStage],
    },
  ];
}

export function decisionOptionRows(
  analysis: RelationshipAnalysis,
): Array<{ id: DecisionOptionId; text: string; selected: boolean }> {
  return (["A", "B", "C", "D"] as DecisionOptionId[]).map((id) => ({
    id,
    text: analysis.decision.options[id],
    selected: analysis.decision.recommended === id,
  }));
}
