/**
 * Human-readable causal explanations from graph.
 */

import { DYNAMICS_STATE_LABELS } from "../display";
import type { CausalExplanation, CausalGraph, StateTransition } from "./causalTypes";

function summarize(transition: StateTransition, causes: CausalExplanation["causes"]): string {
  const fromLabel = DYNAMICS_STATE_LABELS[transition.from];
  const toLabel = DYNAMICS_STATE_LABELS[transition.to];
  const top = causes[0];

  if (!top) {
    return `关系从「${fromLabel}」变为「${toLabel}」，暂无明显单一触发事件。`;
  }

  return `关系从「${fromLabel}」变为「${toLabel}」，主要由「${top.reason}」（强度 ${(top.strength * 100).toFixed(0)}%）引起。`;
}

export function generateExplanation(graph: CausalGraph): CausalExplanation[] {
  return graph.transitions.map((t) => {
    const relatedEdges = graph.edges.filter((e) => e.toTransitionId === t.id);

    const causes = relatedEdges
      .map((e) => {
        const event = graph.nodes.find((n) => n.id === e.fromEventId);
        return {
          eventId: e.fromEventId,
          type: event?.type ?? "message",
          strength: e.weight,
          reason: e.reason,
        };
      })
      .sort((a, b) => b.strength - a.strength);

    return {
      transition: t,
      causes,
      summary: summarize(t, causes),
    };
  });
}
