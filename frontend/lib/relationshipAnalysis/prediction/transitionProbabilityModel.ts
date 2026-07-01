/**
 * Base Markov-style transition probabilities (rule-based, no ML).
 */

import type { PredictionState } from "./predictionTypes";

export type TransitionMatrix = Record<
  PredictionState,
  Partial<Record<PredictionState, number>>
>;

export function computeBaseTransitionMatrix(): TransitionMatrix {
  return {
    warm: {
      warm: 0.6,
      neutral: 0.3,
      cold: 0.08,
      breaking: 0.02,
    },
    neutral: {
      warm: 0.15,
      neutral: 0.5,
      cold: 0.25,
      breaking: 0.08,
      broken: 0.02,
    },
    cold: {
      neutral: 0.1,
      cold: 0.55,
      breaking: 0.25,
      broken: 0.1,
    },
    breaking: {
      cold: 0.2,
      breaking: 0.5,
      broken: 0.3,
    },
    broken: {
      broken: 1.0,
    },
  };
}

export function clamp(v: number): number {
  return Math.max(0, Math.min(1, v));
}

export function normalizeProbabilities(
  rows: Array<{ state: PredictionState; probability: number }>,
): Array<{ state: PredictionState; probability: number }> {
  const sum = rows.reduce((a, b) => a + b.probability, 0);
  if (sum <= 0) {
    return rows.map((x) => ({ ...x, probability: +(1 / rows.length).toFixed(3) }));
  }
  return rows.map((x) => ({
    state: x.state,
    probability: +(x.probability / sum).toFixed(3),
  }));
}

export function matrixRow(
  matrix: TransitionMatrix,
  current: PredictionState,
): Array<{ state: PredictionState; probability: number }> {
  const row = matrix[current] ?? {};
  return Object.entries(row).map(([state, probability]) => ({
    state: state as PredictionState,
    probability: probability ?? 0,
  }));
}
