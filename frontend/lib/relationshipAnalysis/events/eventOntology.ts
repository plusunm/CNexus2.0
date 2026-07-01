/**
 * Event Ontology v1 — CNexus behavior primitives (not relationship interpretation).
 */

export const EVENT_ONTOLOGY_VERSION = "1.0" as const;

export type EventActor = string;

export type EmotionDirection = "cold" | "neutral" | "warm";

export type MessageEvent = {
  type: "message";
  actor: EventActor;
  target?: EventActor;
  text: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

export type ReplyDelayEvent = {
  type: "reply_delay";
  actor: EventActor;
  target: EventActor;
  value: number;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

export type InitiativeEvent = {
  type: "initiative";
  actor: EventActor;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

export type SilenceEvent = {
  type: "silence";
  duration: number;
  timestamp: number;
  actor?: EventActor;
  metadata?: Record<string, unknown>;
};

export type IgnoreEvent = {
  type: "ignore";
  actor: EventActor;
  target: EventActor;
  value: number;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

export type EmotionShiftEvent = {
  type: "emotion_shift";
  actor: EventActor;
  direction: EmotionDirection;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

export type IntensityEvent = {
  type: "intensity";
  delta: number;
  timestamp: number;
  actor?: EventActor;
  metadata?: Record<string, unknown>;
};

export type BehaviorEvent =
  | MessageEvent
  | ReplyDelayEvent
  | InitiativeEvent
  | SilenceEvent
  | IgnoreEvent
  | EmotionShiftEvent
  | IntensityEvent;

export type ConversationTurn = {
  timestamp: string | number;
  speaker: string;
  text: string;
};

export type EventStream = {
  version: typeof EVENT_ONTOLOGY_VERSION;
  entities: string[];
  events: BehaviorEvent[];
};

export const EVENT_TYPES = [
  "message",
  "reply_delay",
  "initiative",
  "silence",
  "ignore",
  "emotion_shift",
  "intensity",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];
