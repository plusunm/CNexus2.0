"use client";

import { useEffect, useRef, useState } from "react";
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
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";
import { SbSegment, SbSettingRow } from "./second-brain/SbUIKit";

type Props = {
  disabled?: boolean;
};

/** Second-brain only: 回答风格 + 回复方式（记忆范围在输入框上方单独设置）。 */
export function ChatPreferencesDropdown({ disabled }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [open, setOpen] = useState(false);
  const [thinkingMode, setThinkingMode] = useState<ThinkingMode>(() => loadThinkingMode());
  const [converseMode, setConverseMode] = useState<ConverseMode>(() => loadConverseMode());
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const summary =
    thinkingMode === "precision" ? copy("precision") : copy("emergent");

  return (
    <div ref={rootRef} className="relative shrink-0 mb-0.5">
      <button
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

      {open && (
        <div
          className="absolute bottom-full right-0 mb-2 w-[min(100vw-2rem,320px)] rounded-xl border p-4 shadow-xl z-50 space-y-4"
          style={{ borderColor: t.border, backgroundColor: t.surface }}
          role="dialog"
          aria-label={copy("chatPreferences")}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold" style={{ color: t.text }}>
              {copy("chatPreferences")}
            </p>
            <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ color: t.textMuted, backgroundColor: t.chatBg }}>
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
              }}
              options={[
                { id: "fast", label: copy("converseFast") },
                { id: "deep", label: copy("converseDeep") },
                { id: "raw", label: copy("converseRaw") },
              ]}
            />
          </SbSettingRow>
        </div>
      )}
    </div>
  );
}
