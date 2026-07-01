"use client";

import clsx from "clsx";
import type { RelationshipDynamicsState } from "@/lib/relationshipAnalysis";
import { DYNAMICS_STATE_LABELS, DYNAMICS_STATE_ORDER } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";

const STATE_COLORS: Record<RelationshipDynamicsState, string> = {
  warm: "#5eead4",
  neutral: "#94a3b8",
  cold: "#60a5fa",
  breaking: "#f472b6",
  broken: "#ef4444",
};

type Props = {
  current: RelationshipDynamicsState;
  className?: string;
};

export function PhaseIndicator({ current, className }: Props) {
  const t = useMindTheme();
  const idx = DYNAMICS_STATE_ORDER.indexOf(current);

  return (
    <div className={clsx("space-y-2", className)}>
      <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: t.textLight }}>
        关系阶段
      </p>
      <div className="flex items-center gap-1">
        {DYNAMICS_STATE_ORDER.map((state, i) => {
          const active = state === current;
          const passed = i <= idx;
          const color = STATE_COLORS[state];
          return (
            <div key={state} className="flex-1 flex flex-col items-center gap-1 min-w-0">
              <div
                className="h-2 w-full rounded-full transition-all"
                style={{
                  backgroundColor: passed ? color : t.border,
                  opacity: active ? 1 : passed ? 0.55 : 0.25,
                  boxShadow: active ? `0 0 8px ${color}66` : undefined,
                }}
              />
              <span
                className="text-[9px] truncate w-full text-center"
                style={{ color: active ? color : t.textMuted, fontWeight: active ? 600 : 400 }}
              >
                {DYNAMICS_STATE_LABELS[state]}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
