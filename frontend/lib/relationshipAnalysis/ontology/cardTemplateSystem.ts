/**
 * Card Template System — ontology-constrained instantiation (not free generation).
 */

import type { DecisionModelCard } from "../types/modelCard";
import type { DecisionOptionId, RelationshipAnalysis } from "../types/relationship";
import {
  familyDecisionLogic,
  getModelFamily,
  MODEL_ONTOLOGY,
  type ModelFamilyId,
} from "./modelOntology";
import type { ModelRouteResult } from "./modelRouter";

export class OntologyValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "OntologyValidationError";
  }
}

function clampList(items: string[], schema: { minItems: number; maxItems: number }): string[] {
  const cleaned = items.map((r) => r.trim()).filter(Boolean);
  if (cleaned.length > schema.maxItems) return cleaned.slice(0, schema.maxItems);
  return cleaned;
}

function mergeSignalSlots(template: string[], fromAnalysis: string[], max: number): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const row of [...fromAnalysis, ...template]) {
    const t = row.replace(/^当前/, "").trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
    if (out.length >= max) break;
  }
  return out;
}

function fillGenericMeta(analysis: RelationshipAnalysis): Pick<DecisionModelCard, "title" | "problemType" | "modelSummary"> {
  const text = analysis.meta.sourceInput;
  if (/offer|跳槽|辞职|求职|裸辞/.test(text)) {
    return {
      title: "职业机会评估模型",
      problemType: "机会评估",
      modelSummary: "用于在机会评估场景下，将信号、风险与行动压缩为可复用决策结构",
    };
  }
  if (/领导|老板|上级|甩锅|加薪/.test(text)) {
    return {
      title: "职场上下级决策模型",
      problemType: "权益与沟通",
      modelSummary: "用于在权益与沟通场景下，将信号、风险与行动压缩为可复用决策结构",
    };
  }
  if (/朋友|借钱|边界/.test(text)) {
    return {
      title: "人际边界决策模型",
      problemType: "边界设定",
      modelSummary: "用于在边界设定场景下，将信号、风险与行动压缩为可复用决策结构",
    };
  }
  if (/催婚|父母|家庭/.test(text)) {
    return {
      title: "家庭压力决策模型",
      problemType: "家庭压力",
      modelSummary: "用于在家庭压力场景下，将信号、风险与行动压缩为可复用决策结构",
    };
  }
  if (/城市|回老家|人生/.test(text)) {
    return {
      title: "人生方向选择模型",
      problemType: "人生选择",
      modelSummary: "用于在人生选择场景下，将信号、风险与行动压缩为可复用决策结构",
    };
  }
  const family = MODEL_ONTOLOGY.generic;
  return {
    title: family.title,
    problemType: family.problemType,
    modelSummary: family.modelSummary,
  };
}

/** Instantiate a model card from ontology template — structure is fixed, only slots filled. */
export function instantiateModelCard(
  analysis: RelationshipAnalysis,
  route: ModelRouteResult,
): DecisionModelCard {
  const family = route.family;
  const structure = family.canonicalStructure;
  const tpl = family.template;
  const rec: DecisionOptionId = analysis.decision.recommended;

  const meta =
    route.familyId === "generic"
      ? fillGenericMeta(analysis)
      : { title: family.title, problemType: family.problemType, modelSummary: family.modelSummary };

  const positive = mergeSignalSlots(
    tpl.signalModel.keyPositiveSignals,
    analysis.signals.positive,
    structure.signalModel.keyPositiveSignals.maxItems,
  );
  const negative = mergeSignalSlots(
    tpl.signalModel.keyNegativeSignals,
    analysis.signals.negative,
    structure.signalModel.keyNegativeSignals.maxItems,
  );

  const actionLogic = structure.decisionModel.fixedBranches[rec];

  const coreRisks = clampList(
    [analysis.uncertainty.risk, ...tpl.riskModel.coreRisks],
    structure.riskModel.coreRisks,
  );
  const misjudgment = clampList(
    [
      ...analysis.uncertainty.missingInfo.slice(0, 1).map((r) => `信息缺口：${r}`),
      ...tpl.riskModel.misjudgmentSources,
    ],
    structure.riskModel.misjudgmentSources,
  );

  const actions =
    analysis.actions.length >= structure.actionTemplate.minItems
      ? analysis.actions.slice(0, structure.actionTemplate.maxItems)
      : tpl.actionTemplate.slice(0, structure.actionTemplate.maxItems);

  const card: DecisionModelCard = {
    ...meta,
    libraryModelId: route.familyId === "generic" ? undefined : route.familyId,
    signalModel: { keyPositiveSignals: positive, keyNegativeSignals: negative },
    decisionModel: {
      triggerConditions: [...tpl.triggerConditions],
      recommendedActionLogic: actionLogic,
    },
    riskModel: { coreRisks, misjudgmentSources: misjudgment },
    actionTemplate: actions,
    reusabilityTags: [...tpl.reusabilityTags],
  };

  validateCardOntology(card, route.familyId);
  return card;
}

export function validateCardOntology(card: DecisionModelCard, familyId: ModelFamilyId): void {
  const family = getModelFamily(familyId);
  const s = family.canonicalStructure;

  if (familyId !== "generic" && card.libraryModelId !== familyId) {
    throw new OntologyValidationError(`libraryModelId must be ${familyId}`);
  }

  if (card.title !== family.title && familyId !== "generic") {
    throw new OntologyValidationError("title drift from ontology");
  }

  const neg = card.signalModel.keyNegativeSignals;
  if (neg.length < s.signalModel.keyNegativeSignals.minItems && familyId !== "generic") {
    throw new OntologyValidationError("keyNegativeSignals below ontology minimum");
  }

  const triggers = card.decisionModel.triggerConditions;
  if (triggers.length !== family.template.triggerConditions.length && familyId !== "generic") {
    throw new OntologyValidationError("triggerConditions must match ontology template count");
  }

  for (const tag of s.reusabilityTags.required) {
    if (!card.reusabilityTags.includes(tag)) {
      throw new OntologyValidationError(`missing required tag: ${tag}`);
    }
  }
  for (const tag of card.reusabilityTags) {
    if (!s.reusabilityTags.allowed.includes(tag) && familyId !== "generic") {
      throw new OntologyValidationError(`tag not in ontology allowlist: ${tag}`);
    }
  }
}

/** LLM may only fill signal/action slot text — structure re-anchored to ontology baseline. */
export function constrainLlmFillToOntology(
  baseline: DecisionModelCard,
  llmPayload: Record<string, unknown>,
  familyId: ModelFamilyId,
): DecisionModelCard {
  const family = getModelFamily(familyId);
  const structure = family.canonicalStructure;

  const signalIn =
    (llmPayload.signalModel as Record<string, unknown> | undefined) ??
    (llmPayload.signal_model as Record<string, unknown> | undefined);
  let positive = baseline.signalModel.keyPositiveSignals;
  let negative = baseline.signalModel.keyNegativeSignals;

  if (signalIn) {
    const llmPos = signalIn.keyPositiveSignals ?? signalIn.key_positive_signals;
    const llmNeg = signalIn.keyNegativeSignals ?? signalIn.key_negative_signals;
    if (Array.isArray(llmPos) && llmPos.length > 0) {
      positive = mergeSignalSlots(
        family.template.signalModel.keyPositiveSignals,
        llmPos.map(String),
        structure.signalModel.keyPositiveSignals.maxItems,
      );
    }
    if (Array.isArray(llmNeg) && llmNeg.length > 0) {
      negative = mergeSignalSlots(
        family.template.signalModel.keyNegativeSignals,
        llmNeg.map(String),
        structure.signalModel.keyNegativeSignals.maxItems,
      );
    }
  }

  const llmActions = llmPayload.actionTemplate ?? llmPayload.action_template;
  let actions = baseline.actionTemplate;
  if (Array.isArray(llmActions) && llmActions.length >= structure.actionTemplate.minItems) {
    actions = clampList(llmActions.map(String), structure.actionTemplate);
  }

  const merged: DecisionModelCard = {
    ...baseline,
    signalModel: { keyPositiveSignals: positive, keyNegativeSignals: negative },
    actionTemplate: actions,
    title: baseline.title,
    problemType: baseline.problemType,
    modelSummary: baseline.modelSummary,
    libraryModelId: baseline.libraryModelId,
    decisionModel: baseline.decisionModel,
    riskModel: baseline.riskModel,
    reusabilityTags: baseline.reusabilityTags,
  };

  validateCardOntology(merged, familyId);
  return merged;
}

export function ontologyTemplateForPrompt(familyId: ModelFamilyId): Record<string, unknown> {
  const family = getModelFamily(familyId);
  return {
    family_id: familyId,
    title: family.title,
    problem_type: family.problemType,
    model_summary: family.modelSummary,
    canonical_structure: family.canonicalStructure,
    template: family.template,
    decision_logic: familyDecisionLogic(family),
    fill_policy: "只能填充 signal_model 与 action_template 的槽位文本，不得改变结构、标签、触发条件、决策分支",
  };
}

export function buildCardFromLibraryModel(
  analysis: RelationshipAnalysis,
  route: ModelRouteResult,
): DecisionModelCard | null {
  if (route.familyId === "generic" && route.isRomanceDomain) return null;
  return instantiateModelCard(analysis, route);
}
