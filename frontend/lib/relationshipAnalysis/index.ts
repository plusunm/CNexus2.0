/**
 * Public surface — UI & hooks import from here only.
 */

export type {
  RelationshipAnalysis,
  RelationshipAnalysisCard,
  RelationshipAnalysisMeta,
  RelationshipAnalysisState,
  RelationshipAnalysisSignals,
  RelationshipAnalysisUncertainty,
  RelationshipAnalysisDecision,
  LevelBand,
  RelationshipStage,
  DecisionOptionId,
} from "./types/relationship";

export type {
  DecisionModelCard,
  DecisionModelSignalModel,
  DecisionModelDecisionModel,
  DecisionModelRiskModel,
} from "./types/modelCard";

export {
  RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
  DECISION_OPTION_IDS,
} from "./types/relationship";

export {
  DECISION_EXAMPLE_DOMAINS,
  DECISION_ANALYSIS_EXAMPLE_GROUPS,
  RELATIONSHIP_ANALYSIS_EXAMPLE_GROUPS,
  RELATIONSHIP_ANALYSIS_EXAMPLES,
  decisionExamplesByDomain,
  type DecisionExamplePrompt,
  type DecisionExampleDomain,
} from "./examplePrompts";

export { backendToCanonical, toRelationshipCard, mapBackendToRelationshipAnalysis } from "./adapter";
export {
  assertRelationshipAnalysis,
  assertRelationshipAnalysisCard,
  isRelationshipAnalysis,
  RelationshipAnalysisSchemaError,
} from "./assertCanonical";
export {
  stateRows,
  decisionOptionRows,
  LEVEL_BAND_LABELS,
  RELATIONSHIP_STAGE_LABELS,
  DYNAMICS_STATE_LABELS,
  DYNAMICS_STATE_ORDER,
} from "./display";

export { ChatParser, chatParser, parseChatLog, type ParsedConversation } from "./import/chatParser";

export {
  RELATIONSHIP_MEMORY_STORE_KEY,
  listRelationshipMemories,
  getRelationshipMemory,
  saveRelationshipMemory,
  deleteRelationshipMemory,
  buildMemoryRecord,
  newRelationshipMemoryId,
  type RelationshipMemoryRecord,
} from "./memory/relationshipMemoryStore";
export {
  listRelationshipCards,
  saveRelationshipCard,
  getRelationshipCard,
  deleteRelationshipCard,
  coerceRelationshipCard,
} from "./cardStorage";

export { ruleBasedModelCard, cardListSummary } from "./modelCardCoerce";

export {
  MODEL_ONTOLOGY,
  getModelFamily,
  familyDecisionLogic,
  type ModelFamily,
  type ModelFamilyId,
} from "./ontology/modelOntology";

export {
  routeModel,
  routeModel as routeRelationshipModel,
  libraryModelLabel,
  RELATIONSHIP_LIBRARY_PHASE_ORDER,
  type ModelRouteResult,
  type RelationshipLibraryModelId,
} from "./ontology/modelRouter";

export {
  instantiateModelCard,
  validateCardOntology,
  constrainLlmFillToOntology,
  ontologyTemplateForPrompt,
  buildCardFromLibraryModel,
} from "./ontology/cardTemplateSystem";

export {
  RELATIONSHIP_DECISION_LIBRARY,
  type RelationshipLibraryModel,
} from "./library/relationshipDecisionLibrary";

export type { ConverseBlockingRaw, StatusRaw } from "./converseRaw";

export type {
  BehaviorEvent,
  ConversationTurn,
  EventStream,
  EventType,
  EmotionDirection,
} from "./events/eventOntology";

export { EVENT_ONTOLOGY_VERSION, EVENT_TYPES } from "./events/eventOntology";
export { extractEventsFromConversation } from "./events/ruleBasedEventExtraction";

export type {
  RelationshipTimeline,
  TimelineSegment,
  SegmentMetrics,
  RelationshipDynamicsState,
} from "./timeline/timelineSchema";

export { TIMELINE_SCHEMA_VERSION } from "./timeline/timelineSchema";
export { buildTimeline } from "./timeline/timelineBuilder";

export {
  transitionState,
  initialState,
  dynamicsToCanonicalStage,
  metricsToLevelBands,
} from "./stateEngine/stateTransitionEngine";

export {
  runCognitivePipeline,
  enrichPipelineLayers,
  runTimelineAnalysisHybrid,
  pipelineToModelCard,
  type CognitivePipelineResult,
} from "./pipeline/cognitivePipeline";

export {
  analyzeRelationshipHybrid,
  type AnalyzeRelationshipResult,
} from "./analyzeRelationshipHybrid";

export { buildOfflineRelationshipAnalysis, isNetworkFetchError } from "./offlineAnalysis";

export type {
  CausalEventType,
  EventNode,
  RelationshipState as CausalRelationshipState,
  StateTransition,
  CausalEdge,
  CausalGraph,
  CausalExplanation,
  CausalEngineResult,
} from "./causal/causalTypes";

export { scoreEventImpact, scoreWithProximity } from "./causal/causalScoring";
export { detectTransitions, transitionsFromTimeline, transitionId } from "./causal/causalInference";
export { buildCausalGraph, edgeReason } from "./causal/causalGraphBuilder";
export { generateExplanation } from "./causal/explanationGenerator";
export { eventsFromStream, behaviorEventToNode } from "./causal/eventAdapter";
export { runCausalEngine, runCausalEngineFromPipeline } from "./causal/causalEngine";

export type {
  PredictionState,
  StateProbability,
  StatePredictionResult,
  DriftTrend,
  DriftForecast,
  ScenarioActionId,
  ScenarioResult,
  PredictionResult,
} from "./prediction/predictionTypes";

export { SCENARIO_LABELS, DRIFT_TREND_LABELS } from "./prediction/predictionTypes";
export {
  computeBaseTransitionMatrix,
  normalizeProbabilities,
  type TransitionMatrix,
} from "./prediction/transitionProbabilityModel";
export { predictNextState } from "./prediction/statePredictor";
export { forecastDrift } from "./prediction/driftForecast";
export { simulateScenarios } from "./prediction/scenarioSimulator";
export { runPredictionEngine, runPredictionFromPipeline } from "./prediction/predictionEngine";

export type {
  CounterfactualActionType,
  CounterfactualAction,
  StateDistribution,
  CounterfactualOutcome,
  CounterfactualResult,
  PolicyTrend,
  RankedPolicy,
  CounterfactualEngineResult,
} from "./counterfactual/counterfactualTypes";

export { ACTION_SPACE } from "./counterfactual/actionSpace";
export { simulateOutcome, computeRiskScore } from "./counterfactual/outcomeSimulator";
export {
  evaluatePolicies,
  computePolicyScore,
  inferPolicyTrend,
  distributionBars,
} from "./counterfactual/policyEvaluator";
export {
  runCounterfactualEngine,
  runCounterfactualFromPipeline,
} from "./counterfactual/counterfactualEngine";
