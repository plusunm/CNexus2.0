"use client";

import {
  THINKING_MODE_OPTIONS,
  type ThinkingMode,
  saveThinkingMode,
} from "@/lib/thinkingMode";
import { useMindTheme } from "./MindUiProvider";
import { floatTy } from "@/lib/floatTypography";

export function ChatThinkingModeSelect({
  value,
  onChange,
  compact = false,
  disabled = false,
  className = "",
}: {
  value: ThinkingMode;
  onChange: (mode: ThinkingMode) => void;
  compact?: boolean;
  disabled?: boolean;
  className?: string;
}) {
  const t = useMindTheme();
  const activeHint = THINKING_MODE_OPTIONS.find((option) => option.id === value)?.hint ?? "";

  return (
    <div className={className}>
      <div
        className={`flex flex-wrap gap-1 p-0.5 rounded-lg border ${compact ? "" : "sm:flex-nowrap"}`}
        style={{ borderColor: t.border, backgroundColor: t.bg }}
        role="radiogroup"
        aria-label="认知思考模式"
      >
        {THINKING_MODE_OPTIONS.map((option) => {
          const active = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              title={option.hint}
              className={`flex-1 min-w-[5.5rem] px-2 py-1.5 rounded-md transition-colors disabled:opacity-50 ${
                compact ? floatTy.caption : "text-[11px]"
              }`}
              style={{
                color: active ? t.purple : t.textLight,
                backgroundColor: active ? t.purpleSoft : "transparent",
                fontWeight: active ? 600 : 400,
              }}
              onClick={() => {
                if (option.id === value) return;
                saveThinkingMode(option.id);
                onChange(option.id);
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      {activeHint ? (
        <p
          className={`mt-1.5 px-0.5 ${compact ? floatTy.caption : "text-[10px]"}`}
          style={{ color: t.textLight }}
        >
          {activeHint}
        </p>
      ) : null}
    </div>
  );
}
