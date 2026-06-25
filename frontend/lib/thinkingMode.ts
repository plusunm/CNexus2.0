import { notifyChatPrefsChanged } from "./chatPrefs";

export type ThinkingMode = "precision" | "emergent";

export type ThinkingModeOption = {
  id: ThinkingMode;
  label: string;
  hint: string;
};

export const THINKING_MODE_OPTIONS: ThinkingModeOption[] = [
  { id: "precision", label: "绝对精确", hint: "温度 0 · 严守审计与 Provenance · 拒绝幻觉" },
  { id: "emergent", label: "自动涌现", hint: "共识熵驱动温度 · 跨节点联想 · Reflection Log 留痕" },
];

const STORAGE_KEY = "cnexus-thinking-mode";

export function loadThinkingMode(): ThinkingMode {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === "precision" || value === "emergent") {
      return value;
    }
  } catch {
    /* ignore */
  }
  return "precision";
}

export function saveThinkingMode(mode: ThinkingMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
    notifyChatPrefsChanged();
  } catch {
    /* ignore */
  }
}

export function thinkingModeLabel(mode: ThinkingMode): string {
  return THINKING_MODE_OPTIONS.find((option) => option.id === mode)?.label ?? mode;
}

export function thinkingModeHint(mode: ThinkingMode): string {
  return THINKING_MODE_OPTIONS.find((option) => option.id === mode)?.hint ?? "";
}
