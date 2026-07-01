/**
 * What-if scenario simulation — action → outcome probabilities.
 */

import type { PredictionState, ScenarioActionId, ScenarioResult } from "./predictionTypes";
import { SCENARIO_LABELS } from "./predictionTypes";
import { normalizeProbabilities } from "./transitionProbabilityModel";

function simulateAction(action: ScenarioActionId, state: PredictionState): ScenarioResult["outcomes"] {
  if (action === "continue_silence") {
    const raw =
      state === "warm" || state === "neutral"
        ? [
            { state: "neutral" as PredictionState, probability: 0.35 },
            { state: "cold" as PredictionState, probability: 0.45 },
            { state: "breaking" as PredictionState, probability: 0.2 },
          ]
        : [
            { state: "cold" as PredictionState, probability: 0.5 },
            { state: "breaking" as PredictionState, probability: 0.3 },
            { state: "broken" as PredictionState, probability: 0.2 },
          ];
    return normalizeProbabilities(raw);
  }

  if (action === "immediate_reply") {
    const raw =
      state === "cold" || state === "breaking"
        ? [
            { state: "neutral" as PredictionState, probability: 0.45 },
            { state: "cold" as PredictionState, probability: 0.35 },
            { state: "warm" as PredictionState, probability: 0.2 },
          ]
        : [
            { state: "warm" as PredictionState, probability: 0.55 },
            { state: "neutral" as PredictionState, probability: 0.35 },
            { state: "cold" as PredictionState, probability: 0.1 },
          ];
    return normalizeProbabilities(raw);
  }

  // send_light_message
  const raw = [
    { state: "neutral" as PredictionState, probability: 0.5 },
    { state: "warm" as PredictionState, probability: 0.25 },
    { state: "cold" as PredictionState, probability: 0.25 },
  ];
  return normalizeProbabilities(raw);
}

export function simulateScenarios(currentState: PredictionState): ScenarioResult[] {
  const actions: ScenarioActionId[] = [
    "immediate_reply",
    "send_light_message",
    "continue_silence",
  ];

  return actions.map((action) => ({
    action,
    label: SCENARIO_LABELS[action],
    outcomes: simulateAction(action, currentState),
  }));
}
