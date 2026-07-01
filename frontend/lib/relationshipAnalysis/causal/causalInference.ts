/**
 * State transition detection — event-stream rules + timeline bridge.
 */

import type { RelationshipTimeline } from "../timeline/timelineSchema";
import type { EventNode, RelationshipState, StateTransition } from "./causalTypes";

export function transitionId(t: Pick<StateTransition, "from" | "to" | "timestamp">): string {
  return `${t.from}->${t.to}@${t.timestamp}`;
}

/** Event-stream rule inference (standalone causal path). */
export function detectTransitions(events: EventNode[]): StateTransition[] {
  const transitions: StateTransition[] = [];
  if (events.length === 0) return transitions;

  let currentState: RelationshipState = "warm";

  for (let i = 1; i < events.length; i++) {
    const e = events[i];
    const prev: RelationshipState = currentState;
    const next: RelationshipState = inferStateFromEvent(prev, e);

    if (next !== prev) {
      const row: StateTransition = {
        id: transitionId({ from: prev, to: next, timestamp: e.timestamp }),
        from: prev,
        to: next,
        timestamp: e.timestamp,
      };
      transitions.push(row);
      currentState = next;
    }
  }

  return transitions;
}

function inferStateFromEvent(state: RelationshipState, event: EventNode): RelationshipState {
  if (state === "warm") {
    if (event.type === "reply_delay" && (event.value ?? 0) > 7200) return "neutral";
    if (event.type === "emotion_shift" && event.direction === "cold") return "neutral";
  }

  if (state === "neutral") {
    if (event.type === "silence" && (event.value ?? 0) >= 86400) return "cold";
    if (event.type === "reply_delay" && (event.value ?? 0) > 14400) return "cold";
  }

  if (state === "cold") {
    if (event.type === "ignore") return "breaking";
    if (event.type === "silence" && (event.value ?? 0) >= 259200) return "breaking";
  }

  if (state === "breaking") {
    if (event.type === "silence" && (event.value ?? 0) > 604800) return "broken";
    if (event.type === "ignore" && (event.value ?? 0) > 86400) return "broken";
  }

  if (state === "warm" && event.type === "initiative") return "warm";

  return state;
}

/** Prefer timeline state engine output when available. */
export function transitionsFromTimeline(timeline: RelationshipTimeline): StateTransition[] {
  const rows: StateTransition[] = [];

  for (const h of timeline.stateHistory) {
    const seg = timeline.segments[h.segmentIndex];
    const timestamp = seg?.end ?? seg?.start ?? 0;
    rows.push({
      id: transitionId({ from: h.from, to: h.to, timestamp }),
      from: h.from,
      to: h.to,
      timestamp,
    });
  }

  if (rows.length === 0 && timeline.segments.length > 0) {
    const first = timeline.segments[0];
    const initial = first.stateSnapshot;
    const final = timeline.currentState;
    if (initial !== final) {
      const last = timeline.segments[timeline.segments.length - 1];
      const timestamp = last?.end ?? last?.start ?? 0;
      rows.push({
        id: transitionId({ from: initial, to: final, timestamp }),
        from: initial,
        to: final,
        timestamp,
      });
    }
  }

  return rows;
}
