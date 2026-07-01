/**
 * Counterfactual Decision Engine v2.3 — types.
 */

import type { PredictionState } from "../prediction/predictionTypes";
import type { DriftTrend } from "../prediction/predictionTypes";

export type CounterfactualActionType = "reply" | "silence" | "light_message" | "wait";

export interface CounterfactualAction {
  id: string;
  label: string;
  type: CounterfactualActionType;
}

export type StateDistribution = Record<PredictionState, number>;

export interface CounterfactualOutcome {
  stateDistribution: StateDistribution;
  delta: Partial<Record<PredictionState, number>>;
  riskScore: number;
}

export interface CounterfactualResult {
  action: CounterfactualAction;
  outcome: CounterfactualOutcome;
}

export type PolicyTrend = Extract<DriftTrend, "improving" | "stable" | "declining">;

export interface RankedPolicy {
  action: CounterfactualAction;
  score: number;
  expectedTrend: PolicyTrend;
  outcome: CounterfactualOutcome;
}

export interface CounterfactualEngineResult {
  bestAction: RankedPolicy;
  policies: RankedPolicy[];
  results: CounterfactualResult[];
}

export const ALL_PREDICTION_STATES: PredictionState[] = [
  "warm",
  "neutral",
  "cold",
  "breaking",
  "broken",
];

export function emptyDistribution(): StateDistribution {
  return { warm: 0, neutral: 0, cold: 0, breaking: 0, broken: 0 };
}
