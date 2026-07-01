"use client";

import clsx from "clsx";
import { ArrowRight } from "lucide-react";
import {
  RELATIONSHIP_LIBRARY_PHASE_ORDER,
  RELATIONSHIP_DECISION_LIBRARY,
  libraryModelLabel,
  type RelationshipLibraryModelId,
} from "@/lib/relationshipAnalysis/library/relationshipDecisionLibrary";
import { useMindTheme } from "../../MindUiProvider";

const PHASE_COLORS: Record<RelationshipLibraryModelId, string> = {
  ambiguous_phase: "#f472b6",
  cold_phase: "#60a5fa",
  breakdown_phase: "#94a3b8",
};

type Props = {
  activeId?: string;
  className?: string;
};

export function RelationshipPhaseMap({ activeId, className }: Props) {
  const t = useMindTheme();

  if (!activeId || !RELATIONSHIP_LIBRARY_PHASE_ORDER.includes(activeId as RelationshipLibraryModelId)) {
    return null;
  }

  const active = activeId as RelationshipLibraryModelId;

  return (
    <div
      className={clsx("flex flex-wrap items-center gap-1.5 text-[10px]", className)}
      aria-label="关系决策模型阶段"
    >
      {RELATIONSHIP_LIBRARY_PHASE_ORDER.map((id, idx) => {
        const isActive = id === active;
        const color = PHASE_COLORS[id];
        return (
          <span key={id} className="flex items-center gap-1.5">
            {idx > 0 && (
              <ArrowRight className="w-3 h-3 shrink-0 opacity-40" style={{ color: t.textMuted }} />
            )}
            <span
              className={clsx(
                "px-2 py-1 rounded-full border font-medium transition",
                isActive ? "shadow-sm" : "opacity-55",
              )}
              style={{
                borderColor: isActive ? `${color}88` : t.border,
                backgroundColor: isActive ? `${color}18` : "transparent",
                color: isActive ? color : t.textMuted,
              }}
              title={RELATIONSHIP_DECISION_LIBRARY[id].modelSummary}
            >
              {libraryModelLabel(id)}
            </span>
          </span>
        );
      })}
    </div>
  );
}
