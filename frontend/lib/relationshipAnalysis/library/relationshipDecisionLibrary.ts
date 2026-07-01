/**
 * Relationship Decision Library — backward-compatible view over Model Ontology.
 * SSOT: ontology/modelOntology.ts
 */

import type { DecisionOptionId } from "../types/relationship";
import { familyDecisionLogic, MODEL_ONTOLOGY, type ModelFamilyId } from "../ontology/modelOntology";
import { routeModel, type ModelRouteResult } from "../ontology/modelRouter";
import {
  buildCardFromLibraryModel,
  instantiateModelCard,
  validateCardOntology,
  constrainLlmFillToOntology,
  ontologyTemplateForPrompt,
} from "../ontology/cardTemplateSystem";

export type RelationshipLibraryModelId = Exclude<ModelFamilyId, "generic">;

export type RelationshipLibraryModel = {
  id: RelationshipLibraryModelId;
  phaseOrder: 0 | 1 | 2;
  nextPhase?: RelationshipLibraryModelId;
  title: string;
  problemType: string;
  modelSummary: string;
  signalModel: { keyPositiveSignals: string[]; keyNegativeSignals: string[] };
  triggerConditions: string[];
  decisionLogic: string;
  decisionLogicByOption: Record<DecisionOptionId, string>;
  riskModel: { coreRisks: string[]; misjudgmentSources: string[] };
  actionTemplate: string[];
  reusabilityTags: string[];
};

function toLibraryView(id: RelationshipLibraryModelId): RelationshipLibraryModel {
  const family = MODEL_ONTOLOGY[id];
  const branches = family.canonicalStructure.decisionModel.fixedBranches;
  return {
    id,
    phaseOrder: family.phaseOrder ?? 0,
    nextPhase: family.nextPhase as RelationshipLibraryModelId | undefined,
    title: family.title,
    problemType: family.problemType,
    modelSummary: family.modelSummary,
    signalModel: family.template.signalModel,
    triggerConditions: family.template.triggerConditions,
    decisionLogic: familyDecisionLogic(family),
    decisionLogicByOption: branches,
    riskModel: family.template.riskModel,
    actionTemplate: family.template.actionTemplate,
    reusabilityTags: [...family.template.reusabilityTags],
  };
}

export const RELATIONSHIP_LIBRARY_PHASE_ORDER: RelationshipLibraryModelId[] = [
  "ambiguous_phase",
  "cold_phase",
  "breakdown_phase",
];

export const RELATIONSHIP_DECISION_LIBRARY: Record<
  RelationshipLibraryModelId,
  RelationshipLibraryModel
> = {
  ambiguous_phase: toLibraryView("ambiguous_phase"),
  cold_phase: toLibraryView("cold_phase"),
  breakdown_phase: toLibraryView("breakdown_phase"),
};

export { routeModel, routeModel as routeRelationshipModel, libraryModelLabel } from "../ontology/modelRouter";
export type { ModelRouteResult };

export {
  buildCardFromLibraryModel,
  instantiateModelCard,
  validateCardOntology,
  constrainLlmFillToOntology,
  ontologyTemplateForPrompt,
};

export {
  MODEL_ONTOLOGY,
  getModelFamily,
  familyDecisionLogic,
  type ModelFamily,
  type ModelFamilyId,
} from "../ontology/modelOntology";
