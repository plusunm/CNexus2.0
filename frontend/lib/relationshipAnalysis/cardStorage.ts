import { assertRelationshipAnalysis, assertRelationshipAnalysisCard } from "./assertCanonical";
import { toRelationshipCard } from "./adapter";
import { ruleBasedModelCard } from "./modelCardCoerce";
import { isFullDecisionModelCard, isLegacyCardEnvelope } from "./types/modelCard";
import type { RelationshipAnalysis, RelationshipAnalysisCard } from "./types/relationship";

const STORAGE_KEY = "cnexus-relationship-cards-v1";

function readRaw(): unknown[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(cards: RelationshipAnalysisCard[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
  } catch {
    /* ignore quota */
  }
}

function parseCard(value: unknown): RelationshipAnalysisCard | null {
  if (!value || typeof value !== "object") return null;
  try {
    assertRelationshipAnalysis(value);
  } catch {
    return null;
  }
  const row = value as RelationshipAnalysis & { card?: unknown };
  const card = row.card;
  if (isFullDecisionModelCard(card)) {
    try {
      assertRelationshipAnalysisCard(value);
      return value as RelationshipAnalysisCard;
    } catch {
      /* fall through */
    }
  }
  if (isLegacyCardEnvelope(card)) {
    const upgraded = ruleBasedModelCard(row);
    return { ...row, card: { ...upgraded, title: card.title || upgraded.title } };
  }
  return toRelationshipCard(row);
}

export function listRelationshipCards(): RelationshipAnalysisCard[] {
  return readRaw()
    .map(parseCard)
    .filter((row): row is RelationshipAnalysisCard => row !== null)
    .sort((a, b) => b.meta.createdAt.localeCompare(a.meta.createdAt));
}

export function saveRelationshipCard(card: RelationshipAnalysisCard): RelationshipAnalysisCard[] {
  assertRelationshipAnalysisCard(card);
  const existing = listRelationshipCards();
  const next = [card, ...existing.filter((row) => row.meta.id !== card.meta.id)];
  writeAll(next);
  return next;
}

export function getRelationshipCard(id: string): RelationshipAnalysisCard | null {
  return listRelationshipCards().find((row) => row.meta.id === id) ?? null;
}

export function deleteRelationshipCard(id: string): RelationshipAnalysisCard[] {
  const next = listRelationshipCards().filter((row) => row.meta.id !== id);
  writeAll(next);
  return next;
}

export function coerceRelationshipCard(value: unknown): RelationshipAnalysisCard | null {
  return parseCard(value);
}

export type { RelationshipAnalysis, RelationshipAnalysisCard };
