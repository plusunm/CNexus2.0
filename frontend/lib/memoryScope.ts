import { notifyChatPrefsChanged } from "./chatPrefs";

export type MemoryScope = "local" | "trusted" | "network";

/** Default scope on fresh install / system open — local memory only. */
export const DEFAULT_MEMORY_SCOPE: MemoryScope = "local";

export type MemoryScopeOption = {
  id: MemoryScope;
  label: string;
  hint: string;
};

export const MEMORY_SCOPE_OPTIONS: MemoryScopeOption[] = [
  { id: "local", label: "本机记忆", hint: "本机创建或拥有的记忆与文档" },
  { id: "trusted", label: "组群记忆", hint: "本机 + 已信任设备上的记忆" },
  { id: "network", label: "全网记忆", hint: "搜索网络中所有已缓存来源" },
];

const STORAGE_KEY = "cnexus-memory-scope";

export function loadMemoryScope(): MemoryScope {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === "local" || value === "trusted" || value === "network") {
      return value;
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_MEMORY_SCOPE;
}

/** Persist default local scope when user has never chosen a range (first open). */
export function ensureDefaultMemoryScopeOnBoot(): MemoryScope {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === "local" || value === "trusted" || value === "network") {
      return value;
    }
    localStorage.setItem(STORAGE_KEY, DEFAULT_MEMORY_SCOPE);
    notifyChatPrefsChanged();
  } catch {
    /* ignore */
  }
  return DEFAULT_MEMORY_SCOPE;
}

export function saveMemoryScope(scope: MemoryScope): void {
  try {
    localStorage.setItem(STORAGE_KEY, scope);
    notifyChatPrefsChanged();
  } catch {
    /* ignore */
  }
}
