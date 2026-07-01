/**
 * Timeline Schema v1 — temporal structure over Event Stream.
 */

import type { BehaviorEvent } from "../events/eventOntology";

export const TIMELINE_SCHEMA_VERSION = "1.0" as const;

export type RelationshipDynamicsState = "warm" | "neutral" | "cold" | "breaking" | "broken";

export type SegmentMetrics = {
  replyLatencyAvg: number;
  initiativeRatio: number;
  silenceRatio: number;
  messageCount: number;
  ignoreCount: number;
  emotionColdCount: number;
};

export type TimelineSegment = {
  start: number;
  end: number;
  stateSnapshot: RelationshipDynamicsState;
  metrics: SegmentMetrics;
};

export type RelationshipTimeline = {
  version: typeof TIMELINE_SCHEMA_VERSION;
  entities: string[];
  events: BehaviorEvent[];
  segments: TimelineSegment[];
  /** Final state after state engine */
  currentState: RelationshipDynamicsState;
  stateHistory: Array<{ segmentIndex: number; from: RelationshipDynamicsState; to: RelationshipDynamicsState }>;
};
