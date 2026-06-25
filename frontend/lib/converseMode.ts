import { notifyChatPrefsChanged } from "./chatPrefs";

export type ConverseMode = "fast" | "deep" | "raw";

export type ConverseModeOption = {
  id: ConverseMode;
  label: string;
  hint: string;
};

export const CONVERSE_MODE_OPTIONS: ConverseModeOption[] = [
  { id: "fast", label: "快速思考", hint: "少量记忆注入，优先响应速度" },
  { id: "deep", label: "深度推理", hint: "长上下文 + 更多记忆召回，适合复杂问题" },
  { id: "raw", label: "仅原文", hint: "不注入记忆，只把输入原文发给模型" },
];

const STORAGE_KEY = "cnexus-converse-mode";

export function loadConverseMode(): ConverseMode {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === "fast" || value === "deep" || value === "raw") {
      return value;
    }
  } catch {
    /* ignore */
  }
  return "fast";
}

export function saveConverseMode(mode: ConverseMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
    notifyChatPrefsChanged();
  } catch {
    /* ignore */
  }
}

export function converseModeLabel(mode: ConverseMode): string {
  return CONVERSE_MODE_OPTIONS.find((option) => option.id === mode)?.label ?? mode;
}

export function converseModeHint(mode: ConverseMode): string {
  return CONVERSE_MODE_OPTIONS.find((option) => option.id === mode)?.hint ?? "";
}
