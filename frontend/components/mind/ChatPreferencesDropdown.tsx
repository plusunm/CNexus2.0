"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, SlidersHorizontal } from "lucide-react";
import {
  loadConverseMode,
  saveConverseMode,
  type ConverseMode,
} from "@/lib/converseMode";
import {
  loadThinkingMode,
  saveThinkingMode,
  type ThinkingMode,
} from "@/lib/thinkingMode";
import {
  loadMemoryScope,
  MEMORY_SCOPE_OPTIONS,
  saveMemoryScope,
  type MemoryScope,
} from "@/lib/memoryScope";
import { notifyChatPrefsChanged } from "@/lib/chatPrefs";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";
import { SbSegment, SbSettingRow } from "./second-brain/SbUIKit";

type Props = {
  disabled?: boolean;
  /** Float panel: include memory scope + render menu in portal to avoid clipping */
  includeMemoryScope?: boolean;
  portal?: boolean;
};

export function ChatPreferencesDropdown({
  disabled,
  includeMemoryScope = false,
  portal = false,
}: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [open, setOpen] = useState(false);
  const [thinkingMode, setThinkingMode] = useState<ThinkingMode>(() => loadThinkingMode());
  const [converseMode, setConverseMode] = useState<ConverseMode>(() => loadConverseMode());
  const [memoryScope, setMemoryScope] = useState<MemoryScope>(() => loadMemoryScope());
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuPos, setMenuPos] = useState<{ left: number; bottom: number; width: number } | null>(
    null,
  );

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  useLayoutEffect(() => {
    if (!open || !portal || !buttonRef.current) {
      setMenuPos(null);
      return;
    }
    const measure = () => {
      const rect = buttonRef.current?.getBoundingClientRect();
      if (!rect) return;
      const width = Math.min(320, window.innerWidth - 16);
      setMenuPos({
        left: Math.min(Math.max(8, rect.right - width), window.innerWidth - width - 8),
        bottom: window.innerHeight - rect.top + 8,
        width,
      });
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [open, portal]);

  const summary =
    thinkingMode === "precision" ? copy("precision") : copy("emergent");

  const menuBody = (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold" style={{ color: t.text }}>
          {copy("chatPreferences")}
        </p>
        <span
          className="text-[10px] px-2 py-0.5 rounded-full"
          style={{ color: t.textMuted, backgroundColor: t.chatBg }}
        >
          {summary}
        </span>
      </div>

      <SbSettingRow label={copy("thinkingStyle")}>
        <SbSegment
          value={thinkingMode}
          disabled={disabled}
          tone="purple"
          onChange={(mode) => {
            saveThinkingMode(mode);
            setThinkingMode(mode);
            notifyChatPrefsChanged();
          }}
          options={[
            { id: "precision", label: copy("precision") },
            { id: "emergent", label: copy("emergent") },
          ]}
        />
      </SbSettingRow>

      <SbSettingRow label={copy("converseMode")}>
        <SbSegment
          value={converseMode}
          disabled={disabled}
          tone="blue"
          onChange={(mode) => {
            saveConverseMode(mode);
            setConverseMode(mode);
            notifyChatPrefsChanged();
          }}
          options={[
            { id: "fast", label: copy("converseFast") },
            { id: "deep", label: copy("converseDeep") },
            { id: "raw", label: copy("converseRaw") },
          ]}
        />
      </SbSettingRow>

      {includeMemoryScope && converseMode !== "raw" ? (
        <SbSettingRow label="记忆范围">
          <SbSegment
            value={memoryScope}
            disabled={disabled}
            tone="teal"
            onChange={(scope) => {
              saveMemoryScope(scope);
              setMemoryScope(scope);
              notifyChatPrefsChanged();
            }}
            options={MEMORY_SCOPE_OPTIONS.map((option) => ({
              id: option.id,
              label: option.label,
            }))}
          />
        </SbSettingRow>
      ) : null}
    </>
  );

  const menuPanel = open ? (
    <div
      ref={portal ? menuRef : undefined}
      className={
        portal
          ? "fixed rounded-xl border p-4 shadow-xl z-[100001] space-y-4 max-h-[min(70vh,420px)] overflow-y-auto cnexus-float-scroll"
          : "absolute bottom-full right-0 mb-2 w-[min(100vw-2rem,320px)] rounded-xl border p-4 shadow-xl z-50 space-y-4 max-h-[min(50vh,360px)] overflow-y-auto cnexus-float-scroll"
      }
      style={
        portal && menuPos
          ? {
              left: menuPos.left,
              bottom: menuPos.bottom,
              width: menuPos.width,
              borderColor: t.border,
              backgroundColor: t.surface,
            }
          : { borderColor: t.border, backgroundColor: t.surface }
      }
      role="dialog"
      aria-label={copy("chatPreferences")}
    >
      {menuBody}
    </div>
  ) : null;

  return (
    <div ref={rootRef} className="relative shrink-0 mb-0.5">
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={copy("chatPreferences")}
        className="h-9 px-2 rounded-lg flex items-center gap-0.5 border disabled:opacity-50 transition"
        style={{
          borderColor: open ? "#5eead466" : t.border,
          color: open ? "#5eead4" : t.textMuted,
          backgroundColor: open ? "rgba(94,234,212,0.08)" : t.surface,
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <SlidersHorizontal className="w-3.5 h-3.5" />
        <ChevronDown className={`w-3 h-3 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {!portal && menuPanel}
      {portal && typeof document !== "undefined" && menuPanel
        ? createPortal(menuPanel, document.body)
        : null}
    </div>
  );
}
