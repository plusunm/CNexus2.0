/**
 * Relationship Memory Store v2 — timeline + state persistence (localStorage).
 */

import type { EventStream } from "../events/eventOntology";
import type { RelationshipTimeline, RelationshipDynamicsState } from "../timeline/timelineSchema";
import type { RelationshipAnalysis } from "../types/relationship";
import type { DecisionModelCard } from "../types/modelCard";
import type { CausalEngineResult } from "../causal/causalTypes";
import type { PredictionResult } from "../prediction/predictionTypes";
import type { CounterfactualEngineResult } from "../counterfactual/counterfactualTypes";

export const RELATIONSHIP_MEMORY_STORE_KEY = "cnexus-relationship-memory-v2";

export type RelationshipMemoryRecord = {
  id: string;
  title: string;
  participants: [string, string];
  eventStream: EventStream;
  timeline: RelationshipTimeline;
  relationshipState: RelationshipDynamicsState;
  analysis?: RelationshipAnalysis;
  card?: DecisionModelCard;
  causal?: CausalEngineResult;
  prediction?: PredictionResult;
  counterfactual?: CounterfactualEngineResult;
  createdAt: number;
  updatedAt: number;
};

function readRaw(): unknown[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RELATIONSHIP_MEMORY_STORE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(records: RelationshipMemoryRecord[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(RELATIONSHIP_MEMORY_STORE_KEY, JSON.stringify(records));
    window.dispatchEvent(new CustomEvent("cnexus-relationship-memory-updated"));
  } catch {
    /* quota */
  }
}

function coerceRecord(value: unknown): RelationshipMemoryRecord | null {
  if (!value || typeof value !== "object") return null;
  const row = value as RelationshipMemoryRecord;
  if (!row.id || !row.timeline || !row.eventStream) return null;
  return row;
}

export function newRelationshipMemoryId(): string {
  return `rm-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function listRelationshipMemories(): RelationshipMemoryRecord[] {
  return readRaw()
    .map(coerceRecord)
    .filter((r): r is RelationshipMemoryRecord => r !== null)
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getRelationshipMemory(id: string): RelationshipMemoryRecord | null {
  return listRelationshipMemories().find((r) => r.id === id) ?? null;
}

export function saveRelationshipMemory(record: RelationshipMemoryRecord): RelationshipMemoryRecord {
  const now = Date.now();
  const next: RelationshipMemoryRecord = {
    ...record,
    updatedAt: now,
    createdAt: record.createdAt || now,
  };
  const existing = listRelationshipMemories().filter((r) => r.id !== next.id);
  writeAll([next, ...existing]);
  return next;
}

export function deleteRelationshipMemory(id: string): void {
  writeAll(listRelationshipMemories().filter((r) => r.id !== id));
}

export function buildMemoryRecord(input: {
  title: string;
  participants: [string, string];
  eventStream: EventStream;
  timeline: RelationshipTimeline;
  relationshipState: RelationshipDynamicsState;
  analysis?: RelationshipAnalysis;
  card?: DecisionModelCard;
  causal?: CausalEngineResult;
  prediction?: PredictionResult;
  counterfactual?: CounterfactualEngineResult;
  id?: string;
}): RelationshipMemoryRecord {
  const now = Date.now();
  return {
    id: input.id ?? newRelationshipMemoryId(),
    title: input.title,
    participants: input.participants,
    eventStream: input.eventStream,
    timeline: input.timeline,
    relationshipState: input.relationshipState,
    analysis: input.analysis,
    card: input.card,
    causal: input.causal,
    prediction: input.prediction,
    counterfactual: input.counterfactual,
    createdAt: now,
    updatedAt: now,
  };
}
