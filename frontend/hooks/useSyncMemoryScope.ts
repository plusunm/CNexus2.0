"use client";

import { useCallback, useEffect, useState } from "react";
import { CHAT_PREFS_CHANGED } from "@/lib/chatPrefs";
import { loadMemoryScope, saveMemoryScope, type MemoryScope } from "@/lib/memoryScope";

/** Shared memory scope — synced with chat prefs via localStorage. */
export function useSyncMemoryScope(): [MemoryScope, (scope: MemoryScope) => void] {
  const [scope, setScopeState] = useState<MemoryScope>("local");

  useEffect(() => {
    setScopeState(loadMemoryScope());
    const onChange = () => setScopeState(loadMemoryScope());
    window.addEventListener(CHAT_PREFS_CHANGED, onChange);
    return () => window.removeEventListener(CHAT_PREFS_CHANGED, onChange);
  }, []);

  const setScope = useCallback((next: MemoryScope) => {
    saveMemoryScope(next);
    setScopeState(next);
  }, []);

  return [scope, setScope];
}
