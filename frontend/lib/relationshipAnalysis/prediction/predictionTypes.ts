/**
 * Prediction Engine v2.2 — probability forecast types.
 */

export type PredictionState =
  | "warm"
  | "neutral"
  | "cold"
  | "breaking"
  | "broken";

export interface StateProbability {
  state: PredictionState;
  probability: number;
}

export interface StatePredictionResult {
  currentState: PredictionState;
  nextStateProbabilities: StateProbability[];
}

export type DriftTrend = "improving" | "stable" | "declining" | "accelerating_cold";

export interface DriftForecast {
  trend: DriftTrend;
  velocity: number;
  riskWindowDays: number;
}

export type ScenarioActionId = "immediate_reply" | "continue_silence" | "send_light_message";

export interface ScenarioResult {
  action: ScenarioActionId;
  label: string;
  outcomes: StateProbability[];
}

export interface PredictionResult {
  statePrediction: StatePredictionResult;
  drift: DriftForecast;
  scenarios: ScenarioResult[];
}

export const SCENARIO_LABELS: Record<ScenarioActionId, string> = {
  immediate_reply: "立即回复",
  continue_silence: "继续沉默",
  send_light_message: "发一条轻量消息",
};

export const DRIFT_TREND_LABELS: Record<DriftTrend, string> = {
  improving: "回暖",
  stable: "平稳",
  declining: "下滑",
  accelerating_cold: "加速降温",
};
