/**
 * Timeline Builder — Event Stream → segmented timeline with metrics.
 */

import type { BehaviorEvent } from "../events/eventOntology";
import { DAY_MS } from "../events/ruleBasedEventExtraction";
import type {
  RelationshipDynamicsState,
  RelationshipTimeline,
  SegmentMetrics,
  TimelineSegment,
} from "./timelineSchema";
import { TIMELINE_SCHEMA_VERSION } from "./timelineSchema";
import { initialState, transitionState } from "../stateEngine/stateTransitionEngine";

const SEGMENT_MAX_SEC = 7 * DAY_MS;

function emptyMetrics(): SegmentMetrics {
  return {
    replyLatencyAvg: 0,
    initiativeRatio: 0,
    silenceRatio: 0,
    messageCount: 0,
    ignoreCount: 0,
    emotionColdCount: 0,
  };
}

function computeMetrics(events: BehaviorEvent[], start: number, end: number): SegmentMetrics {
  const slice = events.filter((e) => e.timestamp >= start && e.timestamp <= end);
  const m = emptyMetrics();
  const delays: number[] = [];
  let initiative = 0;
  let silenceDur = 0;

  for (const e of slice) {
    if (e.type === "message") m.messageCount += 1;
    if (e.type === "reply_delay") delays.push(e.value);
    if (e.type === "initiative") initiative += 1;
    if (e.type === "silence") silenceDur += e.duration;
    if (e.type === "ignore") m.ignoreCount += 1;
    if (e.type === "emotion_shift" && e.direction === "cold") m.emotionColdCount += 1;
  }

  m.replyLatencyAvg = delays.length ? delays.reduce((a, b) => a + b, 0) / delays.length : 0;
  m.initiativeRatio = m.messageCount > 0 ? initiative / m.messageCount : 0;
  const span = Math.max(end - start, 1);
  m.silenceRatio = silenceDur / span;
  return m;
}

function findSegmentBoundaries(events: BehaviorEvent[]): number[] {
  if (events.length === 0) return [];
  const timestamps = events.map((e) => e.timestamp);
  const minTs = timestamps[0];
  const maxTs = timestamps[timestamps.length - 1];
  const bounds: number[] = [minTs];

  for (const e of events) {
    if (e.type === "silence" && e.duration >= DAY_MS) {
      const mid = e.timestamp;
      if (mid > bounds[bounds.length - 1] + 3600) bounds.push(mid);
    }
  }

  let cursor = bounds[bounds.length - 1];
  while (cursor + SEGMENT_MAX_SEC < maxTs) {
    cursor += SEGMENT_MAX_SEC;
    bounds.push(cursor);
  }
  bounds.push(maxTs);
  return [...new Set(bounds)].sort((a, b) => a - b);
}

export function buildTimeline(stream: {
  entities: string[];
  events: BehaviorEvent[];
}): RelationshipTimeline {
  const { entities, events } = stream;
  const sorted = [...events].sort((a, b) => a.timestamp - b.timestamp);

  if (sorted.length === 0) {
    return {
      version: TIMELINE_SCHEMA_VERSION,
      entities,
      events: [],
      segments: [],
      currentState: "neutral",
      stateHistory: [],
    };
  }

  const bounds = findSegmentBoundaries(sorted);
  const segments: TimelineSegment[] = [];
  let state: RelationshipDynamicsState = initialState(sorted);
  const stateHistory: RelationshipTimeline["stateHistory"] = [];

  for (let i = 0; i < bounds.length - 1; i++) {
    const start = bounds[i];
    const end = bounds[i + 1];
    const metrics = computeMetrics(sorted, start, end);
    const prev = state;
    state = transitionState(state, metrics, sorted.filter((e) => e.timestamp >= start && e.timestamp <= end));
    if (state !== prev) {
      stateHistory.push({ segmentIndex: i, from: prev, to: state });
    }
    segments.push({ start, end, stateSnapshot: state, metrics });
  }

  return {
    version: TIMELINE_SCHEMA_VERSION,
    entities,
    events: sorted,
    segments,
    currentState: state,
    stateHistory,
  };
}
