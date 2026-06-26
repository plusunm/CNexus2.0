"use client";

import {
  MEMORY_SCOPE_OPTIONS,
  type MemoryScope,
  saveMemoryScope,
} from "@/lib/memoryScope";
import { useMindTheme } from "./MindUiProvider";
import { floatTy } from "@/lib/floatTypography";

export function ChatMemoryScopeSelect({
  value,
  onChange,
  compact = false,
  hideActiveHint = false,
  disabled = false,
  className = "",
}: {
  value: MemoryScope;
  onChange: (scope: MemoryScope) => void;
  compact?: boolean;
  hideActiveHint?: boolean;
  disabled?: boolean;
  className?: string;
}) {
  const t = useMindTheme();
  const activeHint = MEMORY_SCOPE_OPTIONS.find((option) => option.id === value)?.hint ?? "";

  return (
    <div className={className} data-cnexus-float-scope-select={compact || undefined}>
      <p
        className={`mb-1.5 px-0.5 ${compact ? floatTy.caption : "text-[10px]"}`}
        style={{ color: t.textMuted }}
      >
        记忆范围
      </p>
      <div
        className={`flex flex-wrap gap-1 p-0.5 rounded-lg border ${compact ? "" : "sm:flex-nowrap"}`}
        style={{ borderColor: t.border, backgroundColor: t.bg }}
        role="radiogroup"
        aria-label="对话记忆范围"
      >
        {MEMORY_SCOPE_OPTIONS.map((option) => {
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
                color: active ? "#5eead4" : t.textLight,
                backgroundColor: active ? "rgba(94,234,212,0.14)" : "transparent",
                fontWeight: active ? 600 : 400,
              }}
              onClick={() => {
                if (option.id === value) return;
                saveMemoryScope(option.id);
                onChange(option.id);
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      {activeHint && !hideActiveHint ? (
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
