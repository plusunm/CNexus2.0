/**
 * Rule-based compression: CanonicalSchema → DecisionModelCard via Ontology Template System.
 */

import { routeModel } from "./ontology/modelRouter";
import { instantiateModelCard } from "./ontology/cardTemplateSystem";
import type { RelationshipAnalysis } from "./types/relationship";
import type { DecisionModelCard } from "./types/modelCard";

export function ruleBasedModelCard(analysis: RelationshipAnalysis): DecisionModelCard {
  const route = routeModel(analysis);
  return instantiateModelCard(analysis, route);
}

export function cardListSummary(card: DecisionModelCard): string {
  return card.modelSummary;
}

export { routeModel } from "./ontology/modelRouter";
export { validateCardOntology, constrainLlmFillToOntology } from "./ontology/cardTemplateSystem";
