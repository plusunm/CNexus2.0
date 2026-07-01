/**
 * Causal Engine v2.1 — types for event→transition causality.
 */

export type CausalEventType =
  | "message"
  | "reply_delay"
  | "silence"
  | "initiative"
  | "ignore"
  | "emotion_shift"
  | "intensity";

export type RelationshipState = "warm" | "neutral" | "cold" | "breaking" | "broken";

export interface EventNode {
  id: string;
  type: CausalEventType;
  timestamp: number;
  actor?: string;
  /** Numeric payload: delay seconds, silence duration, etc. */
  value?: number;
  text?: string;
  /** emotion_shift direction */
  direction?: "cold" | "neutral" | "warm";
}

export interface StateTransition {
  id: string;
  from: RelationshipState;
  to: RelationshipState;
  timestamp: number;
}

export interface CausalEdge {
  fromEventId: string;
  toTransitionId: string;
  weight: number;
  reason: string;
}

export interface CausalGraph {
  nodes: EventNode[];
  transitions: StateTransition[];
  edges: CausalEdge[];
}

export interface CausalExplanation {
  transition: StateTransition;
  causes: {
    eventId: string;
    type: CausalEventType;
    strength: number;
    reason: string;
  }[];
  summary: string;
}

export type CausalEngineResult = {
  graph: CausalGraph;
  explanations: CausalExplanation[];
  transitions: StateTransition[];
};
