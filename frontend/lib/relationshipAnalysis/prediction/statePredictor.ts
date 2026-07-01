/**
 * Next-state probability forecast — base matrix + causal shift.
 */

import type { CausalEngineResult } from "../causal/causalTypes";
import type { PredictionState, StatePredictionResult } from "./predictionTypes";
import {
  clamp,
  computeBaseTransitionMatrix,
  matrixRow,
  normalizeProbabilities,
} from "./transitionProbabilityModel";

const COLD_STATES = new Set<PredictionState>(["cold", "breaking", "broken"]);
const WARM_STATES = new Set<PredictionState>(["warm", "neutral"]);

function computeCausalShift(causal: CausalEngineResult): {
  coldBoost: number;
  warmPenalty: number;
} {
  const edges = causal.graph.edges;
  let coldBoost = 0;
  let warmPenalty = 0;

  for (const e of edges) {
    if (e.weight > 0.7) {
      coldBoost += 0.06;
      warmPenalty += 0.04;
    } else if (e.weight > 0.4) {
      coldBoost += 0.03;
    }
    if (e.reason.includes("冷") || e.reason.includes("沉默") || e.reason.includes("断联")) {
      coldBoost += 0.04;
    }
  }

  for (const t of causal.transitions) {
    if (COLD_STATES.has(t.to)) coldBoost += 0.05;
    if (WARM_STATES.has(t.to) && t.from !== t.to) warmPenalty -= 0.02;
  }

  return {
    coldBoost: clamp(coldBoost),
    warmPenalty: clamp(warmPenalty),
  };
}

function applyCausalAdjustment(
  base: Array<{ state: PredictionState; probability: number }>,
  shift: { coldBoost: number; warmPenalty: number },
): Array<{ state: PredictionState; probability: number }> {
  return base.map(({ state, probability }) => {
    let p = probability;
    if (COLD_STATES.has(state)) {
      p *= 1 + shift.coldBoost;
    }
    if (state === "warm") {
      p *= Math.max(0.2, 1 - shift.warmPenalty);
    }
    if (state === "neutral") {
      p *= Math.max(0.3, 1 - shift.warmPenalty * 0.5);
    }
    return { state, probability: clamp(p) };
  });
}

export function predictNextState(
  currentState: PredictionState,
  causal: CausalEngineResult,
): StatePredictionResult {
  const matrix = computeBaseTransitionMatrix();
  const base = matrixRow(matrix, currentState);

  if (base.length === 0) {
    return {
      currentState,
      nextStateProbabilities: [{ state: currentState, probability: 1 }],
    };
  }

  const shift = computeCausalShift(causal);
  const adjusted = applyCausalAdjustment(base, shift);

  return {
    currentState,
    nextStateProbabilities: normalizeProbabilities(adjusted),
  };
}
