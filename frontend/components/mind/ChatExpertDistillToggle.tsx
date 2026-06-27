"use client";

import { useCallback } from "react";
import {
  expertDistillModeLabel,
  loadExpertDistillEnabled,
  resolveExpertSubjectId,
  saveExpertDistillEnabled,
} from "@/lib/expertDistillMode";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";
import { floatTy } from "@/lib/floatTypography";

type Props = {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
  compact?: boolean;
  className?: string;
};

export function ChatExpertDistillToggle({
  enabled,
  onChange,
  disabled = false,
  compact = false,
  className = "",
}: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();

  const toggle = useCallback(async () => {
    if (disabled) return;
    const next = !enabled;
    if (next) {
      await resolveExpertSubjectId();
    }
    saveExpertDistillEnabled(next);
    onChange(next);
  }, [disabled, enabled, onChange]);

  const label = enabled ? copy("expertDistillOn") : copy("expertDistillOff");
  const hint = copy("expertDistillHint");

  return (
    <div className={className}>
      <div
        className={`flex items-center justify-between gap-3 px-2 py-1.5 rounded-lg border ${
          compact ? floatTy.caption : "text-[11px]"
        }`}
        style={{
          borderColor: enabled ? "#5eead466" : t.border,
          backgroundColor: enabled ? "rgba(94,234,212,0.06)" : t.bg,
        }}
      >
        <div className="min-w-0">
          <p className="font-medium truncate" style={{ color: enabled ? "#5eead4" : t.text }}>
            {label}
          </p>
          {!compact ? (
            <p className="text-[10px] mt-0.5 truncate" style={{ color: t.textMuted }} title={hint}>
              {hint}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label={expertDistillModeLabel(enabled)}
          title={hint}
          disabled={disabled}
          onClick={() => void toggle()}
          className="w-9 h-5 rounded-full relative shrink-0 disabled:opacity-50 transition-colors"
          style={{ backgroundColor: enabled ? "#14b8a6" : t.border }}
        >
          <span
            className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all"
            style={{ left: enabled ? "1.125rem" : "0.125rem" }}
          />
        </button>
      </div>
    </div>
  );
}

/** Sync helper for prefs listener — avoids stale closure on mount. */
export function readExpertDistillEnabledFromStorage(): boolean {
  return loadExpertDistillEnabled();
}
