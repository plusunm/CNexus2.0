/** Experience Layer — persona + dialect configuration. */

import type { CognitiveDialect } from "../projection/copyLexicon";

export type { CognitiveDialect };

export type ExperiencePersona = "second-brain" | "cognitive-lab";

export const PERSONA_DEFAULT_DIALECT: Record<ExperiencePersona, CognitiveDialect> = {
  "second-brain": "consumer",
  "cognitive-lab": "research",
};

export const PERSONA_LABELS: Record<
  ExperiencePersona,
  { title: { en: string; zh: string }; subtitle: { en: string; zh: string } }
> = {
  "second-brain": {
    title: { en: "Second Brain", zh: "第二大脑" },
    subtitle: { en: "Chat & remember", zh: "轻松对话与记忆" },
  },
  "cognitive-lab": {
    title: { en: "Cognitive Lab", zh: "认知实验室" },
    subtitle: { en: "Full observability", zh: "完整观测与调试" },
  },
};

/** Overview views that require cognitive-lab persona. */
export const LAB_ONLY_VIEWS = new Set([
  "debugger",
  "flow",
  "token",
  "network",
  "network-connect",
  "network-ops",
  "network-assets",
]);

export type SecondBrainTab =
  | "chat"
  | "memory"
  | "upload"
  | "organize"
  | "network"
  | "connect"
  | "share-memory"
  | "notify"
  | "chat-share"
  | "model"
  | "profile";

export const SECOND_BRAIN_TABS: SecondBrainTab[] = [
  "chat",
  "memory",
  "upload",
  "organize",
  "network",
  "connect",
  "share-memory",
  "notify",
  "chat-share",
  "model",
  "profile",
];

const LEGACY_SECOND_BRAIN_TABS: Record<string, SecondBrainTab> = {
  share: "network",
};

export function normalizeSecondBrainTab(value: string | null | undefined): SecondBrainTab {
  if (isSecondBrainTab(value)) return value;
  if (value && LEGACY_SECOND_BRAIN_TABS[value]) return LEGACY_SECOND_BRAIN_TABS[value];
  return "chat";
}

export function isSecondBrainTab(value: string | null | undefined): value is SecondBrainTab {
  return SECOND_BRAIN_TABS.includes(value as SecondBrainTab);
}
