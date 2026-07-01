/**
 * Counterfactual Decision Engine v2.3 — main entry.
 */

import type { CausalEngineResult } from "../causal/causalTypes";
import type { PredictionResult, PredictionState } from "../prediction/predictionTypes";
import { ACTION_SPACE } from "./actionSpace";
import type { CounterfactualEngineResult, RankedPolicy } from "./counterfactualTypes";
import { evaluatePolicies } from "./policyEvaluator";

function fallbackPolicy(): RankedPolicy {
  const action = ACTION_SPACE[0];
  return {
    action,
    score: 0,
    expectedTrend: "stable",
    outcome: {
      stateDistribution: { warm: 0.2, neutral: 0.5, cold: 0.2, breaking: 0.08, broken: 0.02 },
      delta: {},
      riskScore: 0.3,
    },
  };
}

export function runCounterfactualEngine(
  _currentState: PredictionState,
  prediction: PredictionResult,
  causal: CausalEngineResult,
): CounterfactualEngineResult {
  const policies = evaluatePolicies(ACTION_SPACE, prediction, causal);
  const bestAction = policies[0] ?? fallbackPolicy();

  const results = policies.map((p) => ({
    action: p.action,
    outcome: p.outcome,
  }));

  return { bestAction, policies, results };
}

export function runCounterfactualFromPipeline(
  prediction: PredictionResult,
  causal: CausalEngineResult,
): CounterfactualEngineResult {
  return runCounterfactualEngine(
    prediction.statePrediction.currentState,
    prediction,
    causal,
  );
}
