/**
 * Relationship drift / velocity forecast from causal + timeline signals.
 */

import type { CausalEngineResult } from "../causal/causalTypes";
import type { RelationshipTimeline } from "../timeline/timelineSchema";
import type { DriftForecast, DriftTrend, PredictionState } from "./predictionTypes";
import { clamp } from "./transitionProbabilityModel";

const COLD_ORDER: PredictionState[] = ["warm", "neutral", "cold", "breaking", "broken"];

function stateIndex(s: PredictionState): number {
  return COLD_ORDER.indexOf(s);
}

function countColdSignals(causal: CausalEngineResult): number {
  return causal.graph.edges.filter(
    (e) => e.reason.includes("冷") || e.reason.includes("沉默") || e.reason.includes("断联") || e.weight > 0.7,
  ).length;
}

function timelineDriftSignal(timeline: RelationshipTimeline): number {
  let signal = 0;
  const last = timeline.segments[timeline.segments.length - 1];
  if (!last) return 0;

  const m = last.metrics;
  if (m.silenceRatio > 0.3) signal += 2;
  if (m.replyLatencyAvg > 3600) signal += 2;
  if (m.ignoreCount > 0) signal += 3;
  if (m.emotionColdCount > 0) signal += 2;
  if (m.initiativeRatio < 0.2) signal += 1;

  for (const h of timeline.stateHistory.slice(-2)) {
    if (stateIndex(h.to) > stateIndex(h.from)) signal += 2;
  }

  return signal;
}

export function forecastDrift(causal: CausalEngineResult, timeline: RelationshipTimeline): DriftForecast {
  const coldSignals = countColdSignals(causal) + timelineDriftSignal(timeline);
  const velocity = clamp(coldSignals / 10);

  let trend: DriftTrend = "stable";
  if (velocity > 0.7) trend = "accelerating_cold";
  else if (velocity > 0.4) trend = "declining";
  else if (velocity < 0.15 && timeline.stateHistory.some((h) => stateIndex(h.to) < stateIndex(h.from))) {
    trend = "improving";
  }

  const riskWindowDays = Math.max(1, Math.ceil(14 * (1 - velocity)));

  return { trend, velocity, riskWindowDays };
}
