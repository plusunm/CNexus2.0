/**
 * Rule-based Event Extraction — conversation → Event Stream (no LLM).
 */

import type { BehaviorEvent, ConversationTurn, EventStream } from "./eventOntology";
import { EVENT_ONTOLOGY_VERSION } from "./eventOntology";

const SILENCE_THRESHOLD_SEC = 86400;
const IGNORE_THRESHOLD_SEC = 7200;
const COLD_KEYWORDS = /嗯|哦|好|行|忙|稍后|再说/;
const DAY_MS = 86400;

function parseTimestamp(raw: string | number): number {
  if (typeof raw === "number") return raw > 1e12 ? Math.floor(raw / 1000) : raw;
  const d = Date.parse(String(raw).replace(" ", "T"));
  return Number.isFinite(d) ? Math.floor(d / 1000) : Math.floor(Date.now() / 1000);
}

function inferEntities(turns: ConversationTurn[]): [string, string] {
  const speakers = [...new Set(turns.map((t) => t.speaker.trim()).filter(Boolean))];
  if (speakers.length >= 2) return [speakers[0], speakers[1]];
  if (speakers.length === 1) return [speakers[0], speakers[0] === "A" ? "B" : "A"];
  return ["A", "B"];
}

function emotionDirection(text: string, prevLen: number): "cold" | "neutral" | "warm" | null {
  const len = text.trim().length;
  if (len <= 3 && COLD_KEYWORDS.test(text)) return "cold";
  if (prevLen > 0 && len < prevLen * 0.4 && len < 8) return "cold";
  if (len > 20) return "warm";
  return null;
}

export function extractEventsFromConversation(
  conversation: ConversationTurn[],
  entities?: string[],
): EventStream {
  const sorted = [...conversation]
    .map((t) => ({
      speaker: t.speaker.trim(),
      text: t.text.trim(),
      ts: parseTimestamp(t.timestamp),
    }))
    .filter((t) => t.text)
    .sort((a, b) => a.ts - b.ts);

  const [entityA, entityB] = entities?.length === 2 ? [entities[0], entities[1]] : inferEntities(conversation);
  const events: BehaviorEvent[] = [];
  let lastSpeaker: string | null = null;
  let lastTs = 0;
  let lastTextLen = 0;
  let lastInitiativeTs: Record<string, number> = {};

  for (let i = 0; i < sorted.length; i++) {
    const turn = sorted[i];
    const target = turn.speaker === entityA ? entityB : entityA;

    if (lastTs > 0) {
      const gap = turn.ts - lastTs;
      if (gap >= SILENCE_THRESHOLD_SEC) {
        events.push({
          type: "silence",
          duration: gap,
          timestamp: lastTs + Math.floor(gap / 2),
        });
      }
    }

    if (lastSpeaker !== turn.speaker) {
      const gapSinceInit = lastInitiativeTs[turn.speaker]
        ? turn.ts - lastInitiativeTs[turn.speaker]
        : Infinity;
      if (gapSinceInit > 3600 || !lastInitiativeTs[turn.speaker]) {
        events.push({ type: "initiative", actor: turn.speaker, timestamp: turn.ts });
        lastInitiativeTs[turn.speaker] = turn.ts;
      }
    }

    if (lastSpeaker && lastSpeaker !== turn.speaker && lastTs > 0) {
      const delay = turn.ts - lastTs;
      events.push({
        type: "reply_delay",
        actor: turn.speaker,
        target: lastSpeaker,
        value: delay,
        timestamp: turn.ts,
      });
      if (delay >= IGNORE_THRESHOLD_SEC) {
        events.push({
          type: "ignore",
          actor: turn.speaker,
          target: lastSpeaker,
          value: delay,
          timestamp: turn.ts,
        });
      }
    }

    const shift = emotionDirection(turn.text, lastTextLen);
    if (shift) {
      events.push({
        type: "emotion_shift",
        actor: turn.speaker,
        direction: shift,
        timestamp: turn.ts,
      });
    }

    events.push({
      type: "message",
      actor: turn.speaker,
      target,
      text: turn.text,
      timestamp: turn.ts,
    });

    lastSpeaker = turn.speaker;
    lastTs = turn.ts;
    lastTextLen = turn.text.length;
  }

  if (sorted.length >= 2) {
    const delays = events
      .filter((e): e is Extract<BehaviorEvent, { type: "reply_delay" }> => e.type === "reply_delay")
      .map((e) => e.value);
    const avgDelay = delays.length ? delays.reduce((a, b) => a + b, 0) / delays.length : 0;
    const delta = avgDelay > 3600 ? -0.2 : avgDelay < 600 ? 0.1 : 0;
    if (delta !== 0) {
      events.push({
        type: "intensity",
        delta,
        timestamp: sorted[sorted.length - 1].ts,
      });
    }
  }

  events.sort((a, b) => a.timestamp - b.timestamp);

  return {
    version: EVENT_ONTOLOGY_VERSION,
    entities: [entityA, entityB],
    events,
  };
}

export { SILENCE_THRESHOLD_SEC, IGNORE_THRESHOLD_SEC, DAY_MS };
