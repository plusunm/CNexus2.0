/**
 * Prediction Engine v2.2 — causal + timeline → probability future.
 */

import type { CausalEngineResult } from "../causal/causalTypes";
import type { RelationshipTimeline } from "../timeline/timelineSchema";
import type { PredictionResult, PredictionState } from "./predictionTypes";
import { predictNextState } from "./statePredictor";
import { forecastDrift } from "./driftForecast";
import { simulateScenarios } from "./scenarioSimulator";

export function runPredictionEngine(
  currentState: PredictionState,
  causal: CausalEngineResult,
  timeline: RelationshipTimeline,
): PredictionResult {
  const statePrediction = predictNextState(currentState, causal);
  const drift = forecastDrift(causal, timeline);
  const scenarios = simulateScenarios(currentState);

  return { statePrediction, drift, scenarios };
}

export function runPredictionFromPipeline(
  timeline: RelationshipTimeline,
  causal: CausalEngineResult,
): PredictionResult {
  return runPredictionEngine(timeline.currentState, causal, timeline);
}
