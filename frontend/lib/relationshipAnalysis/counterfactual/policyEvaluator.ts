/**
 * Policy evaluation — rank counterfactual actions by expected utility.
 */

import type { CausalEngineResult } from "../causal/causalTypes";
import type { PredictionResult, PredictionState } from "../prediction/predictionTypes";
import type {
  CounterfactualAction,
  CounterfactualOutcome,
  PolicyTrend,
  RankedPolicy,
  StateDistribution,
} from "./counterfactualTypes";
import { computeRiskScore, simulateOutcome } from "./outcomeSimulator";

const UTILITY: Record<PredictionState, number> = {
  warm: 1.0,
  neutral: 0.6,
  cold: -0.8,
  breaking: -1.2,
  broken: -1.5,
};

export function computePolicyScore(outcome: CounterfactualOutcome): number {
  let score = 0;
  for (const [state, prob] of Object.entries(outcome.stateDistribution) as Array<
    [PredictionState, number]
  >) {
    score += prob * (UTILITY[state] ?? 0);
  }
  score -= outcome.riskScore * 0.3;
  return +score.toFixed(3);
}

export function inferPolicyTrend(outcome: CounterfactualOutcome): PolicyTrend {
  const score = computePolicyScore(outcome);
  if (score > 0.35) return "improving";
  if (score > 0.05) return "stable";
  return "declining";
}

export function evaluatePolicies(
  actions: CounterfactualAction[],
  prediction: PredictionResult,
  causal: CausalEngineResult,
): RankedPolicy[] {
  return actions
    .map((action) => {
      const outcome = simulateOutcome(action, prediction, causal);
      return {
        action,
        score: computePolicyScore(outcome),
        expectedTrend: inferPolicyTrend(outcome),
        outcome,
      };
    })
    .sort((a, b) => b.score - a.score);
}

export function distributionBars(dist: StateDistribution): Array<{ state: PredictionState; value: number }> {
  return (Object.entries(dist) as Array<[PredictionState, number]>)
    .map(([state, value]) => ({ state, value }))
    .sort((a, b) => b.value - a.value);
}
