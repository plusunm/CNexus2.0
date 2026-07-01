/**
 * Rule-based causal impact scoring (0–1).
 */

import type { EventNode } from "./causalTypes";

export function scoreEventImpact(event: EventNode): number {
  switch (event.type) {
    case "reply_delay":
      return Math.min(1, (event.value ?? 0) / 3600);

    case "silence":
      return Math.min(1, (event.value ?? 0) / 86400);

    case "initiative":
      return 0.7;

    case "ignore":
      return 0.9;

    case "emotion_shift":
      return event.direction === "cold" ? 0.8 : 0.4;

    case "intensity":
      return Math.min(1, Math.abs(event.value ?? 0.3));

    case "message":
      return 0.1;

    default:
      return 0.2;
  }
}

/** Boost events that occurred shortly before a transition. */
export function scoreWithProximity(base: number, eventTs: number, transitionTs: number): number {
  const delta = transitionTs - eventTs;
  if (delta < 0) return base * 0.5;
  const windowMs = 7 * 86400 * 1000;
  const proximity = Math.max(0, 1 - delta / windowMs);
  return Math.min(1, base * (0.6 + 0.4 * proximity));
}
