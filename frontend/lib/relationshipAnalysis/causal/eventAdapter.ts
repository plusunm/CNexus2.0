/**
 * BehaviorEvent → EventNode adapter.
 */

import type { BehaviorEvent } from "../events/eventOntology";
import type { CausalEventType, EventNode } from "./causalTypes";

const CAUSAL_TYPES = new Set<CausalEventType>([
  "message",
  "reply_delay",
  "silence",
  "initiative",
  "ignore",
  "emotion_shift",
  "intensity",
]);

function eventValue(e: BehaviorEvent): number | undefined {
  if (e.type === "reply_delay" || e.type === "ignore") return e.value;
  if (e.type === "silence") return e.duration;
  if (e.type === "intensity") return e.delta;
  return undefined;
}

export function behaviorEventToNode(e: BehaviorEvent, index: number): EventNode | null {
  if (!CAUSAL_TYPES.has(e.type as CausalEventType)) return null;

  const node: EventNode = {
    id: `${e.type}-${e.timestamp}-${index}`,
    type: e.type as CausalEventType,
    timestamp: e.timestamp,
    value: eventValue(e),
  };

  if ("actor" in e && e.actor) node.actor = e.actor;
  if (e.type === "message") node.text = e.text;
  if (e.type === "emotion_shift") node.direction = e.direction;

  return node;
}

export function eventsFromStream(events: BehaviorEvent[]): EventNode[] {
  return events
    .map((e, i) => behaviorEventToNode(e, i))
    .filter((n): n is EventNode => n !== null)
    .sort((a, b) => a.timestamp - b.timestamp);
}
