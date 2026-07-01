/**
 * Runtime guard — prevents backend / storage pollution from reaching UI.
 */

import {
  DECISION_OPTION_IDS,
  RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
  type DecisionOptionId,
  type LevelBand,
  type RelationshipAnalysis,
  type RelationshipAnalysisCard,
  type RelationshipStage,
} from "./types/relationship";
import {
  isFullDecisionModelCard,
  isLegacyCardEnvelope,
  type DecisionModelCard,
} from "./types/modelCard";

const LEVEL_BANDS: LevelBand[] = ["high", "medium", "low"];
const STAGES: RelationshipStage[] = ["stable", "cold", "uncertain", "broken"];

function isLevelBand(value: unknown): value is LevelBand {
  return typeof value === "string" && LEVEL_BANDS.includes(value as LevelBand);
}

function isStage(value: unknown): value is RelationshipStage {
  return typeof value === "string" && STAGES.includes(value as RelationshipStage);
}

function isDecisionId(value: unknown): value is DecisionOptionId {
  return typeof value === "string" && DECISION_OPTION_IDS.includes(value as DecisionOptionId);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((row) => typeof row === "string");
}

export class RelationshipAnalysisSchemaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RelationshipAnalysisSchemaError";
  }
}

export function assertRelationshipAnalysis(value: unknown): asserts value is RelationshipAnalysis {
  if (!value || typeof value !== "object") {
    throw new RelationshipAnalysisSchemaError("Expected object");
  }
  const row = value as Record<string, unknown>;

  const meta = row.meta;
  if (!meta || typeof meta !== "object") {
    throw new RelationshipAnalysisSchemaError("Missing meta");
  }
  const m = meta as Record<string, unknown>;
  if (typeof m.id !== "string" || !m.id) {
    throw new RelationshipAnalysisSchemaError("meta.id invalid");
  }
  if (typeof m.sourceInput !== "string" || !m.sourceInput.trim()) {
    throw new RelationshipAnalysisSchemaError("meta.sourceInput invalid");
  }
  if (typeof m.createdAt !== "string" || !m.createdAt) {
    throw new RelationshipAnalysisSchemaError("meta.createdAt invalid");
  }
  if (m.schemaVersion !== RELATIONSHIP_ANALYSIS_SCHEMA_VERSION) {
    throw new RelationshipAnalysisSchemaError("meta.schemaVersion mismatch");
  }

  const state = row.state;
  if (!state || typeof state !== "object") {
    throw new RelationshipAnalysisSchemaError("Missing state");
  }
  const st = state as Record<string, unknown>;
  if (!isLevelBand(st.emotionConnection)) throw new RelationshipAnalysisSchemaError("state.emotionConnection invalid");
  if (!isLevelBand(st.initiativeLevel)) throw new RelationshipAnalysisSchemaError("state.initiativeLevel invalid");
  if (!isLevelBand(st.interactionFrequency)) {
    throw new RelationshipAnalysisSchemaError("state.interactionFrequency invalid");
  }
  if (!isStage(st.relationshipStage)) throw new RelationshipAnalysisSchemaError("state.relationshipStage invalid");

  const signals = row.signals;
  if (!signals || typeof signals !== "object") {
    throw new RelationshipAnalysisSchemaError("Missing signals");
  }
  const sig = signals as Record<string, unknown>;
  if (!isStringArray(sig.positive)) throw new RelationshipAnalysisSchemaError("signals.positive invalid");
  if (!isStringArray(sig.negative)) throw new RelationshipAnalysisSchemaError("signals.negative invalid");

  const uncertainty = row.uncertainty;
  if (!uncertainty || typeof uncertainty !== "object") {
    throw new RelationshipAnalysisSchemaError("Missing uncertainty");
  }
  const un = uncertainty as Record<string, unknown>;
  if (!isStringArray(un.missingInfo)) throw new RelationshipAnalysisSchemaError("uncertainty.missingInfo invalid");
  if (typeof un.risk !== "string" || !un.risk) {
    throw new RelationshipAnalysisSchemaError("uncertainty.risk invalid");
  }

  const decision = row.decision;
  if (!decision || typeof decision !== "object") {
    throw new RelationshipAnalysisSchemaError("Missing decision");
  }
  const dec = decision as Record<string, unknown>;
  const options = dec.options;
  if (!options || typeof options !== "object") {
    throw new RelationshipAnalysisSchemaError("decision.options invalid");
  }
  const opt = options as Record<string, unknown>;
  for (const id of DECISION_OPTION_IDS) {
    if (typeof opt[id] !== "string" || !opt[id]) {
      throw new RelationshipAnalysisSchemaError(`decision.options.${id} invalid`);
    }
  }
  if (!isDecisionId(dec.recommended)) throw new RelationshipAnalysisSchemaError("decision.recommended invalid");
  if (typeof dec.reason !== "string" || !dec.reason) {
    throw new RelationshipAnalysisSchemaError("decision.reason invalid");
  }

  if (!isStringArray(row.actions) || row.actions.length === 0) {
    throw new RelationshipAnalysisSchemaError("actions invalid");
  }
}

function assertDecisionModelCard(value: unknown): asserts value is DecisionModelCard {
  if (!value || typeof value !== "object") {
    throw new RelationshipAnalysisSchemaError("card envelope missing");
  }
  const row = value as Record<string, unknown>;
  if (typeof row.title !== "string" || !row.title.trim()) {
    throw new RelationshipAnalysisSchemaError("card.title invalid");
  }
  if (typeof row.problemType !== "string" || !row.problemType.trim()) {
    throw new RelationshipAnalysisSchemaError("card.problemType invalid");
  }
  if (typeof row.modelSummary !== "string" || !row.modelSummary.trim()) {
    throw new RelationshipAnalysisSchemaError("card.modelSummary invalid");
  }

  const signalModel = row.signalModel;
  if (!signalModel || typeof signalModel !== "object") {
    throw new RelationshipAnalysisSchemaError("card.signalModel invalid");
  }
  const sig = signalModel as Record<string, unknown>;
  if (!isStringArray(sig.keyPositiveSignals)) {
    throw new RelationshipAnalysisSchemaError("card.signalModel.keyPositiveSignals invalid");
  }
  if (!isStringArray(sig.keyNegativeSignals)) {
    throw new RelationshipAnalysisSchemaError("card.signalModel.keyNegativeSignals invalid");
  }

  const decisionModel = row.decisionModel;
  if (!decisionModel || typeof decisionModel !== "object") {
    throw new RelationshipAnalysisSchemaError("card.decisionModel invalid");
  }
  const dec = decisionModel as Record<string, unknown>;
  if (!isStringArray(dec.triggerConditions)) {
    throw new RelationshipAnalysisSchemaError("card.decisionModel.triggerConditions invalid");
  }
  if (typeof dec.recommendedActionLogic !== "string" || !dec.recommendedActionLogic.trim()) {
    throw new RelationshipAnalysisSchemaError("card.decisionModel.recommendedActionLogic invalid");
  }

  const riskModel = row.riskModel;
  if (!riskModel || typeof riskModel !== "object") {
    throw new RelationshipAnalysisSchemaError("card.riskModel invalid");
  }
  const risk = riskModel as Record<string, unknown>;
  if (!isStringArray(risk.coreRisks)) {
    throw new RelationshipAnalysisSchemaError("card.riskModel.coreRisks invalid");
  }
  if (!isStringArray(risk.misjudgmentSources)) {
    throw new RelationshipAnalysisSchemaError("card.riskModel.misjudgmentSources invalid");
  }

  if (!isStringArray(row.actionTemplate) || row.actionTemplate.length === 0) {
    throw new RelationshipAnalysisSchemaError("card.actionTemplate invalid");
  }
  if (!isStringArray(row.reusabilityTags)) {
    throw new RelationshipAnalysisSchemaError("card.reusabilityTags invalid");
  }
}

export function assertRelationshipAnalysisCard(value: unknown): asserts value is RelationshipAnalysisCard {
  assertRelationshipAnalysis(value);
  const card = (value as RelationshipAnalysisCard).card;
  if (isFullDecisionModelCard(card)) {
    assertDecisionModelCard(card);
    return;
  }
  if (isLegacyCardEnvelope(card)) {
    return;
  }
  throw new RelationshipAnalysisSchemaError("card envelope invalid");
}

export function isRelationshipAnalysis(value: unknown): value is RelationshipAnalysis {
  try {
    assertRelationshipAnalysis(value);
    return true;
  } catch {
    return false;
  }
}
