/**
 * Canonical Schema — UI 唯一真相层 (SSOT)
 *
 * UI 组件、Card 存储、未来 /analyze API 输出均只认此契约。
 * 禁止在组件内引用后端字段或做业务推断。
 */

import type { DecisionModelCard } from "./modelCard";

export const RELATIONSHIP_ANALYSIS_SCHEMA_VERSION = "1.0" as const;

export type LevelBand = "high" | "medium" | "low";

export type RelationshipStage = "stable" | "cold" | "uncertain" | "broken";

export type DecisionOptionId = "A" | "B" | "C" | "D";

export const DECISION_OPTION_IDS: DecisionOptionId[] = ["A", "B", "C", "D"];

export type RelationshipAnalysisMeta = {
  id: string;
  sourceInput: string;
  createdAt: string;
  schemaVersion: typeof RELATIONSHIP_ANALYSIS_SCHEMA_VERSION;
};

export type RelationshipAnalysisState = {
  emotionConnection: LevelBand;
  initiativeLevel: LevelBand;
  interactionFrequency: LevelBand;
  relationshipStage: RelationshipStage;
};

export type RelationshipAnalysisSignals = {
  positive: string[];
  negative: string[];
};

export type RelationshipAnalysisUncertainty = {
  missingInfo: string[];
  risk: string;
};

export type RelationshipAnalysisDecision = {
  options: Record<DecisionOptionId, string>;
  recommended: DecisionOptionId;
  reason: string;
};

/** Canonical relationship decision analysis — fixed shape for all renderers. */
export type RelationshipAnalysis = {
  meta: RelationshipAnalysisMeta;
  state: RelationshipAnalysisState;
  signals: RelationshipAnalysisSignals;
  uncertainty: RelationshipAnalysisUncertainty;
  decision: RelationshipAnalysisDecision;
  actions: string[];
};

/** Persisted card envelope — cognitive asset (decision model), not analysis summary. */
export type RelationshipAnalysisCard = RelationshipAnalysis & {
  card: DecisionModelCard;
};
