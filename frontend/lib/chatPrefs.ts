/** Cross-panel sync when chat prefs change (dropdown ↔ input area). */
export const CHAT_PREFS_CHANGED = "cnexus-chat-prefs-changed";

export function notifyChatPrefsChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(CHAT_PREFS_CHANGED));
}
