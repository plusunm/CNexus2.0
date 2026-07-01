/**
 * CNexus counterfactual action space — behavioral input layer.
 */

import type { CounterfactualAction } from "./counterfactualTypes";

export const ACTION_SPACE: CounterfactualAction[] = [
  { id: "reply_now", label: "立即回复", type: "reply" },
  { id: "light_message", label: "轻量消息（低压力）", type: "light_message" },
  { id: "silence", label: "继续沉默", type: "silence" },
  { id: "wait", label: "等待 3 天", type: "wait" },
];
