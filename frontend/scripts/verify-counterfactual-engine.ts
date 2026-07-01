import { parseChatLog } from "../lib/relationshipAnalysis/import/chatParser";
import { runCognitivePipeline } from "../lib/relationshipAnalysis/pipeline/cognitivePipeline";
import { runCounterfactualFromPipeline } from "../lib/relationshipAnalysis/counterfactual/counterfactualEngine";
import { ACTION_SPACE } from "../lib/relationshipAnalysis/counterfactual/actionSpace";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

const sample = parseChatLog(`2025-04-01 10:00 A: hi
2025-04-05 10:00 A: still there?
2025-04-12 10:00 A: hello
2025-04-20 09:00 B: busy`);

const pipeline = runCognitivePipeline(sample.turns);
assert(pipeline.counterfactual, "pipeline includes counterfactual");
assert(pipeline.counterfactual.policies.length === ACTION_SPACE.length, "all actions ranked");
assert(pipeline.counterfactual.bestAction.action.id, "best action id");

const standalone = runCounterfactualFromPipeline(pipeline.prediction, pipeline.causal);
assert(standalone.policies[0].score >= standalone.policies[1]?.score, "sorted by score");

console.log("Counterfactual engine verification: OK");
console.log(`  best: ${standalone.bestAction.action.label}`);
console.log(`  score: ${standalone.bestAction.score}`);
