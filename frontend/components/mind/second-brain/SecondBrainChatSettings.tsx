"use client";

import { useState } from "react";
import { SlidersHorizontal, ChevronDown, ChevronUp } from "lucide-react";
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
import { useMindTheme } from "../MindUiProvider";
import { SbCard, SbSegment, SbSettingRow } from "./SbUIKit";

type Props = {
  disabled?: boolean;
  defaultExpanded?: boolean;
};

export function SecondBrainChatSettings({ disabled, defaultExpanded = true }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [thinkingMode, setThinkingMode] = useState<ThinkingMode>(() => loadThinkingMode());
  const [converseMode, setConverseMode] = useState<ConverseMode>(() => loadConverseMode());

  const activeThinkingHint =
    thinkingMode === "precision" ? copy("precisionHint") : copy("emergentHint");
  const activeConverseHint =
    converseMode === "fast"
      ? copy("converseFastHint")
      : converseMode === "deep"
        ? copy("converseDeepHint")
        : copy("converseRawHint");

  return (
    <SbCard accent="teal" padding="sm" className="shrink-0">
      <button
        type="button"
        className="w-full flex items-center justify-between gap-2 text-left"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2 min-w-0">
          <SlidersHorizontal className="w-4 h-4 shrink-0" style={{ color: "#5eead4" }} />
          <span className="text-xs font-semibold" style={{ color: t.text }}>
            {copy("chatPreferences")}
          </span>
          {!expanded && (
            <span className="text-[10px] truncate" style={{ color: t.textMuted }}>
              {thinkingMode === "precision" ? copy("precision") : copy("emergent")}
              {" · "}
              {converseMode === "fast"
                ? copy("converseFast")
                : converseMode === "deep"
                  ? copy("converseDeep")
                  : copy("converseRaw")}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
        ) : (
          <ChevronDown className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
        )}
      </button>

      {expanded && (
        <div className="mt-3 space-y-4 pt-3 border-t" style={{ borderColor: t.border }}>
          <SbSettingRow label={copy("thinkingStyle")} hint={activeThinkingHint}>
            <SbSegment
              value={thinkingMode}
              disabled={disabled}
              tone="purple"
              onChange={(mode) => {
                saveThinkingMode(mode);
                setThinkingMode(mode);
              }}
              options={[
                { id: "precision", label: copy("precision"), hint: copy("precisionHint") },
                { id: "emergent", label: copy("emergent"), hint: copy("emergentHint") },
              ]}
            />
          </SbSettingRow>

          <SbSettingRow label={copy("converseMode")} hint={activeConverseHint}>
            <SbSegment
              value={converseMode}
              disabled={disabled}
              tone="blue"
              onChange={(mode) => {
                saveConverseMode(mode);
                setConverseMode(mode);
              }}
              options={[
                { id: "fast", label: copy("converseFast"), hint: copy("converseFastHint") },
                { id: "deep", label: copy("converseDeep"), hint: copy("converseDeepHint") },
                { id: "raw", label: copy("converseRaw"), hint: copy("converseRawHint") },
              ]}
            />
          </SbSettingRow>
        </div>
      )}
    </SbCard>
  );
}
