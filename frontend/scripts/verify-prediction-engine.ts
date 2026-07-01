import { parseChatLog } from "../lib/relationshipAnalysis/import/chatParser";
import { runCognitivePipeline } from "../lib/relationshipAnalysis/pipeline/cognitivePipeline";
import { runPredictionFromPipeline } from "../lib/relationshipAnalysis/prediction/predictionEngine";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

const sample = parseChatLog(`2025-04-01 10:00 A: hi
2025-04-01 14:00 B: sorry late
2025-04-05 10:00 A: still there?
2025-04-12 10:00 A: hello
2025-04-20 09:00 B: busy`);

const pipeline = runCognitivePipeline(sample.turns);
assert(pipeline.prediction, "pipeline includes prediction");
assert(pipeline.prediction.statePrediction.nextStateProbabilities.length > 0, "state probs");
assert(pipeline.prediction.scenarios.length === 3, "3 scenarios");

const sum = pipeline.prediction.statePrediction.nextStateProbabilities.reduce(
  (a, b) => a + b.probability,
  0,
);
assert(Math.abs(sum - 1) < 0.05, "probabilities sum ~1");

const standalone = runPredictionFromPipeline(pipeline.timeline, pipeline.causal);
assert(standalone.drift.riskWindowDays >= 1, "risk window");

console.log("Prediction engine verification: OK");
console.log(`  trend: ${standalone.drift.trend}`);
console.log(`  top state: ${standalone.statePrediction.nextStateProbabilities[0]?.state}`);
