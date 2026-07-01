/**
 * State Transition Engine — timeline segments → relationship dynamics state.
 */

import type { BehaviorEvent } from "../events/eventOntology";
import { DAY_MS } from "../events/ruleBasedEventExtraction";
import type { RelationshipDynamicsState, SegmentMetrics } from "../timeline/timelineSchema";

export function initialState(events: BehaviorEvent[]): RelationshipDynamicsState {
  if (events.length === 0) return "neutral";
  const warmish = events.some(
    (e) => e.type === "message" && "text" in e && e.text.length > 15,
  );
  return warmish ? "warm" : "neutral";
}

function isCooling(m: SegmentMetrics): boolean {
  return m.replyLatencyAvg > 1800 && m.initiativeRatio < 0.45;
}

function isCold(m: SegmentMetrics): boolean {
  return (
    m.silenceRatio > 0.25 ||
    (m.initiativeRatio < 0.3 && m.replyLatencyAvg > 3600)
  );
}

function isBreaking(m: SegmentMetrics, events: BehaviorEvent[]): boolean {
  const longSilence = events.some((e) => e.type === "silence" && e.duration >= 2 * DAY_MS);
  return m.ignoreCount >= 2 || (m.emotionColdCount >= 2 && m.initiativeRatio < 0.2) || longSilence;
}

function isDead(m: SegmentMetrics, events: BehaviorEvent[]): boolean {
  const weekSilence = events.some((e) => e.type === "silence" && e.duration >= 7 * DAY_MS);
  return weekSilence || (m.messageCount === 0 && m.silenceRatio > 0.5);
}

export function transitionState(
  state: RelationshipDynamicsState,
  metrics: SegmentMetrics,
  segmentEvents: BehaviorEvent[],
): RelationshipDynamicsState {
  if (state === "warm" && isCooling(metrics)) return "neutral";
  if (state === "neutral" && isCold(metrics)) return "cold";
  if (state === "cold" && isBreaking(metrics, segmentEvents)) return "breaking";
  if (state === "breaking" && isDead(metrics, segmentEvents)) return "broken";

  if (state === "warm" && isCold(metrics)) return "cold";
  if (state === "neutral" && isBreaking(metrics, segmentEvents)) return "breaking";
  if (state === "cold" && isDead(metrics, segmentEvents)) return "broken";

  return state;
}

/** Map dynamics state → CanonicalSchema relationshipStage */
export function dynamicsToCanonicalStage(
  state: RelationshipDynamicsState,
): "stable" | "cold" | "uncertain" | "broken" {
  switch (state) {
    case "warm":
      return "stable";
    case "neutral":
      return "uncertain";
    case "cold":
    case "breaking":
      return "cold";
    case "broken":
      return "broken";
  }
}

export function metricsToLevelBands(metrics: SegmentMetrics): {
  emotionConnection: "high" | "medium" | "low";
  initiativeLevel: "high" | "medium" | "low";
  interactionFrequency: "high" | "medium" | "low";
} {
  const initiativeLevel =
    metrics.initiativeRatio >= 0.5 ? "high" : metrics.initiativeRatio >= 0.25 ? "medium" : "low";
  const interactionFrequency =
    metrics.messageCount >= 10 ? "high" : metrics.messageCount >= 3 ? "medium" : "low";
  const emotionConnection =
    metrics.emotionColdCount >= 2
      ? "low"
      : metrics.emotionColdCount === 0 && metrics.messageCount >= 5
        ? "high"
        : "medium";
  return { emotionConnection, initiativeLevel, interactionFrequency };
}
