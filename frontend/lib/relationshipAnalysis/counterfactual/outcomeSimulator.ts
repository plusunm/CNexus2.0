/**
 * Counterfactual outcome simulation — prediction + action modifier.
 */

import type { CausalEngineResult } from "../causal/causalTypes";
import type { PredictionResult, PredictionState } from "../prediction/predictionTypes";
import { clamp, normalizeProbabilities } from "../prediction/transitionProbabilityModel";
import type {
  CounterfactualAction,
  CounterfactualOutcome,
  StateDistribution,
} from "./counterfactualTypes";
import { ALL_PREDICTION_STATES, emptyDistribution } from "./counterfactualTypes";

type ModifierMap = Partial<Record<PredictionState, number>>;

function getActionModifier(action: CounterfactualAction): ModifierMap {
  switch (action.type) {
    case "reply":
      return { warm: 1.2, neutral: 1.1, cold: 0.7, breaking: 0.5, broken: 0.4 };
    case "light_message":
      return { warm: 1.1, neutral: 1.0, cold: 0.9, breaking: 0.8, broken: 0.7 };
    case "silence":
      return { warm: 0.6, neutral: 0.9, cold: 1.2, breaking: 1.3, broken: 1.1 };
    case "wait":
      return { warm: 0.8, neutral: 1.0, cold: 1.1, breaking: 1.2, broken: 1.05 };
    default:
      return {};
  }
}

function baseDistribution(prediction: PredictionResult): StateDistribution {
  const dist = emptyDistribution();
  for (const row of prediction.statePrediction.nextStateProbabilities) {
    dist[row.state] = row.probability;
  }
  return dist;
}

function applyCausalBias(
  dist: StateDistribution,
  causal: CausalEngineResult,
): StateDistribution {
  let coldBias = 0;
  for (const e of causal.graph.edges) {
    if (e.weight > 0.6) coldBias += 0.02;
  }
  if (coldBias === 0) return dist;

  const next = { ...dist };
  next.cold = clamp(next.cold + coldBias);
  next.breaking = clamp(next.breaking + coldBias * 0.5);
  next.warm = clamp(next.warm - coldBias * 0.5);

  const rows = ALL_PREDICTION_STATES.map((state) => ({ state, probability: next[state] }));
  const normalized = normalizeProbabilities(rows);
  const out = emptyDistribution();
  for (const r of normalized) out[r.state] = r.probability;
  return out;
}

function computeDelta(
  base: StateDistribution,
  adjusted: StateDistribution,
): Partial<Record<PredictionState, number>> {
  const delta: Partial<Record<PredictionState, number>> = {};
  for (const state of ALL_PREDICTION_STATES) {
    delta[state] = +(adjusted[state] - base[state]).toFixed(3);
  }
  return delta;
}

export function computeRiskScore(dist: StateDistribution): number {
  return clamp(dist.cold * 0.6 + dist.breaking * 0.9 + dist.broken * 1.0);
}

export function simulateOutcome(
  action: CounterfactualAction,
  prediction: PredictionResult,
  causal: CausalEngineResult,
): CounterfactualOutcome {
  const base = applyCausalBias(baseDistribution(prediction), causal);
  const modifier = getActionModifier(action);

  const adjustedRows = ALL_PREDICTION_STATES.map((state) => ({
    state,
    probability: base[state] * (modifier[state] ?? 1),
  }));

  const normalized = normalizeProbabilities(adjustedRows);
  const stateDistribution = emptyDistribution();
  for (const r of normalized) stateDistribution[r.state] = r.probability;

  return {
    stateDistribution,
    delta: computeDelta(base, stateDistribution),
    riskScore: computeRiskScore(stateDistribution),
  };
}
