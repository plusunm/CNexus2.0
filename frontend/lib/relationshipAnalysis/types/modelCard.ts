/**
 * Decision Model Card — cognitive asset compressed from CanonicalSchema.
 * Card page output: reusable decision model, not a conversation summary.
 */

export type DecisionModelSignalModel = {
  keyPositiveSignals: string[];
  keyNegativeSignals: string[];
};

export type DecisionModelDecisionModel = {
  triggerConditions: string[];
  recommendedActionLogic: string;
};

export type DecisionModelRiskModel = {
  coreRisks: string[];
  misjudgmentSources: string[];
};

/** Reusable decision model — persisted in card envelope. */
export type DecisionModelCard = {
  title: string;
  problemType: string;
  modelSummary: string;
  /** Relationship Decision Library template id, when routed */
  libraryModelId?: string;
  signalModel: DecisionModelSignalModel;
  decisionModel: DecisionModelDecisionModel;
  riskModel: DecisionModelRiskModel;
  actionTemplate: string[];
  reusabilityTags: string[];
};

/** @deprecated legacy envelope — upgraded on read */
export type LegacyCardEnvelope = {
  title: string;
  summary: string;
};

export function isFullDecisionModelCard(value: unknown): value is DecisionModelCard {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.title === "string" &&
    typeof row.problemType === "string" &&
    typeof row.modelSummary === "string" &&
    typeof row.signalModel === "object" &&
    typeof row.decisionModel === "object" &&
    typeof row.riskModel === "object" &&
    Array.isArray(row.actionTemplate) &&
    Array.isArray(row.reusabilityTags)
  );
}

export function isLegacyCardEnvelope(value: unknown): value is LegacyCardEnvelope {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.title === "string" &&
    typeof row.summary === "string" &&
    row.modelSummary === undefined &&
    row.problemType === undefined
  );
}
