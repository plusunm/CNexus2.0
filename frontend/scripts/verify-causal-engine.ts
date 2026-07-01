import { parseChatLog } from "../lib/relationshipAnalysis/import/chatParser";
import { runCognitivePipeline } from "../lib/relationshipAnalysis/pipeline/cognitivePipeline";
import { runCausalEngine } from "../lib/relationshipAnalysis/causal/causalEngine";
import { eventsFromStream } from "../lib/relationshipAnalysis/causal/eventAdapter";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

const sample = parseChatLog(`2025-04-01 10:00 A: hi
2025-04-01 14:00 B: sorry late
2025-04-05 10:00 A: still there?
2025-04-12 10:00 A: hello`);

const pipeline = runCognitivePipeline(sample.turns);
assert(pipeline.causal, "pipeline includes causal");
assert(Array.isArray(pipeline.causal.explanations), "causal explanations array");

const nodes = eventsFromStream(pipeline.eventStream.events);
const standalone = runCausalEngine(nodes);
assert(standalone.graph.nodes.length === nodes.length, "standalone graph nodes");
assert(standalone.graph.edges.length >= 0, "standalone edges");

console.log("Causal engine verification: OK");
console.log(`  transitions: ${pipeline.causal.transitions.length}`);
console.log(`  explanations: ${pipeline.causal.explanations.length}`);
console.log(`  edges: ${pipeline.causal.graph.edges.length}`);
