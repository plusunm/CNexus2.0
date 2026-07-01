/**
 * Build weighted event → transition causal graph.
 */

import type { CausalEdge, CausalGraph, EventNode, StateTransition } from "./causalTypes";
import { scoreEventImpact, scoreWithProximity } from "./causalScoring";

const TOP_K = 3;
const LOOKBACK_MS = 14 * 86400 * 1000;

export function edgeReason(event: EventNode): string {
  switch (event.type) {
    case "reply_delay":
      return "回复延迟增加导致互动下降";
    case "silence":
      return "长时间沉默降低关系活跃度";
    case "ignore":
      return "未回复导致关系断联风险";
    case "initiative":
      return "主动性变化影响关系推进";
    case "emotion_shift":
      return event.direction === "cold" ? "语气趋冷触发关系降温" : "情绪语气变化影响互动感知";
    case "intensity":
      return "互动强度波动影响关系节奏";
    case "message":
      return "消息内容/频率参与关系状态累积";
    default:
      return "行为影响关系状态变化";
  }
}

export function buildCausalGraph(events: EventNode[], transitions: StateTransition[]): CausalGraph {
  const edges: CausalEdge[] = [];

  for (const t of transitions) {
    const windowStart = t.timestamp - LOOKBACK_MS;
    const candidates = events.filter((e) => e.timestamp <= t.timestamp && e.timestamp >= windowStart);

    const scored = candidates
      .map((event) => {
        const base = scoreEventImpact(event);
        const weight = scoreWithProximity(base, event.timestamp, t.timestamp);
        return { event, weight };
      })
      .filter((s) => s.weight > 0.05)
      .sort((a, b) => b.weight - a.weight)
      .slice(0, TOP_K);

    for (const s of scored) {
      edges.push({
        fromEventId: s.event.id,
        toTransitionId: t.id,
        weight: s.weight,
        reason: edgeReason(s.event),
      });
    }
  }

  return { nodes: events, transitions, edges };
}
