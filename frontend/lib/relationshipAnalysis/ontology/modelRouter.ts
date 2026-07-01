/**
 * Explicit Model Router — scores CanonicalSchema against ontology threshold rules.
 */

import type { RelationshipAnalysis } from "../types/relationship";
import {
  MODEL_ONTOLOGY,
  ROMANCE_MODEL_FAMILY_IDS,
  type ModelFamily,
  type ModelFamilyId,
} from "./modelOntology";

export type ModelRouteResult = {
  familyId: ModelFamilyId;
  family: ModelFamily;
  confidence: number;
  matchedRules: string[];
  reason: string;
  isRomanceDomain: boolean;
};

const NON_ROMANCE =
  /offer|跳槽|辞职|求职|裸辞|领导|老板|上级|甩锅|加薪|同事|朋友|借钱|催婚|父母|家庭|城市|回老家|人生|转行|读博/;

const ROMANCE =
  /恋爱|喜欢|暧昧|分手|冷淡|不理|表白|对象|男友|女友|老公|老婆|相亲|在一起|推进|关系/;

function isRomanceInput(text: string): boolean {
  if (NON_ROMANCE.test(text)) return false;
  return ROMANCE.test(text);
}

type RuleEvaluator = (analysis: RelationshipAnalysis) => boolean;

const RULE_EVALUATORS: Record<string, RuleEvaluator> = {
  keyword_cold: (a) => /冷淡|不理|冷处理|消失|不回|疏远/.test(a.meta.sourceInput),
  stage_cold: (a) => a.state.relationshipStage === "cold",
  low_initiative: (a) => a.state.initiativeLevel === "low",
  low_interaction: (a) => a.state.interactionFrequency === "low",

  keyword_ambiguous: (a) => /暧昧|推进|表白|不明确|在一起吗/.test(a.meta.sourceInput),
  uncertain_high_connection: (a) =>
    a.state.relationshipStage === "uncertain" &&
    a.state.emotionConnection !== "low" &&
    a.state.interactionFrequency !== "low",
  default_romance: () => true,

  keyword_breakup: (a) => /分手|结束|离开|告别|离婚/.test(a.meta.sourceInput),
  stage_broken: (a) => a.state.relationshipStage === "broken",
};

function scoreFamily(familyId: ModelFamilyId, analysis: RelationshipAnalysis): {
  score: number;
  matchedRules: string[];
} {
  const family = MODEL_ONTOLOGY[familyId];
  let score = 0;
  const matchedRules: string[] = [];

  for (const rule of family.thresholdRules) {
    const evaluator = RULE_EVALUATORS[rule.id];
    if (evaluator?.(analysis)) {
      score += rule.weight;
      matchedRules.push(rule.id);
    }
  }
  return { score, matchedRules };
}

export function routeModel(analysis: RelationshipAnalysis): ModelRouteResult {
  const text = analysis.meta.sourceInput;

  if (!isRomanceInput(text)) {
    return {
      familyId: "generic",
      family: MODEL_ONTOLOGY.generic,
      confidence: 1,
      matchedRules: [],
      reason: "非恋爱关系域 → generic 模型族",
      isRomanceDomain: false,
    };
  }

  // Priority tier — explicit keywords override state-derived scores
  if (/分手|结束|离开|告别|离婚/.test(text)) {
    const family = MODEL_ONTOLOGY.breakdown_phase;
    return {
      familyId: "breakdown_phase",
      family,
      confidence: 1,
      matchedRules: ["keyword_breakup"],
      reason: "显式关键词 → 分手期模型族",
      isRomanceDomain: true,
    };
  }
  if (/暧昧|推进|表白|不明确|在一起吗/.test(text)) {
    const family = MODEL_ONTOLOGY.ambiguous_phase;
    return {
      familyId: "ambiguous_phase",
      family,
      confidence: 1,
      matchedRules: ["keyword_ambiguous"],
      reason: "显式关键词 → 暧昧期模型族",
      isRomanceDomain: true,
    };
  }
  if (/冷淡|不理|冷处理|消失|不回|疏远/.test(text)) {
    const family = MODEL_ONTOLOGY.cold_phase;
    return {
      familyId: "cold_phase",
      family,
      confidence: 1,
      matchedRules: ["keyword_cold"],
      reason: "显式关键词 → 冷淡期模型族",
      isRomanceDomain: true,
    };
  }

  let bestId: ModelFamilyId = "ambiguous_phase";
  let bestScore = 0;
  let bestRules: string[] = [];

  for (const familyId of ROMANCE_MODEL_FAMILY_IDS) {
    const { score, matchedRules } = scoreFamily(familyId, analysis);
    if (score > bestScore) {
      bestScore = score;
      bestId = familyId;
      bestRules = matchedRules;
    }
  }

  const family = MODEL_ONTOLOGY[bestId];
  const maxPossible = family.thresholdRules.reduce((sum, r) => sum + r.weight, 0) || 1;
  const confidence = Math.min(1, bestScore / maxPossible);

  const ruleDescriptions = bestRules
    .map((id) => family.thresholdRules.find((r) => r.id === id)?.description)
    .filter(Boolean);

  return {
    familyId: bestId,
    family,
    confidence,
    matchedRules: bestRules,
    reason: ruleDescriptions.length > 0 ? ruleDescriptions.join("；") : "恋爱域默认路由",
    isRomanceDomain: true,
  };
}

/** @deprecated use routeModel */
export const routeRelationshipModel = routeModel;

export type RelationshipLibraryModelId = Exclude<ModelFamilyId, "generic">;

export function libraryModelLabel(id: RelationshipLibraryModelId): string {
  return MODEL_ONTOLOGY[id]?.title.replace("模型", "") ?? id;
}

export const RELATIONSHIP_LIBRARY_PHASE_ORDER: RelationshipLibraryModelId[] = [
  "ambiguous_phase",
  "cold_phase",
  "breakdown_phase",
];
