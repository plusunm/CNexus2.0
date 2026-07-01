/**
 * Causal Engine v2.1 — Event + Timeline → Cause Graph + Explanation.
 */

import type { EventStream } from "../events/eventOntology";
import type { RelationshipTimeline } from "../timeline/timelineSchema";
import type { CausalEngineResult } from "./causalTypes";
import { eventsFromStream } from "./eventAdapter";
import { detectTransitions, transitionsFromTimeline } from "./causalInference";
import { buildCausalGraph } from "./causalGraphBuilder";
import { generateExplanation } from "./explanationGenerator";
import type { EventNode } from "./causalTypes";

export function runCausalEngine(events: EventNode[]): CausalEngineResult {
  const transitions = detectTransitions(events);
  const graph = buildCausalGraph(events, transitions);
  const explanations = generateExplanation(graph);
  return { graph, explanations, transitions };
}

/** Pipeline integration — uses timeline state history as transition SSOT. */
export function runCausalEngineFromPipeline(
  eventStream: EventStream,
  timeline: RelationshipTimeline,
): CausalEngineResult {
  const nodes = eventsFromStream(eventStream.events);
  const transitions = transitionsFromTimeline(timeline);
  const graph = buildCausalGraph(nodes, transitions);
  const explanations = generateExplanation(graph);
  return { graph, explanations, transitions };
}
