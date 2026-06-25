"use client";

import { Brain, FlaskConical } from "lucide-react";
import clsx from "clsx";
import { useMindTheme } from "@/components/mind/MindUiProvider";
import { useLanguageProjection } from "@/components/mind/LanguageProjectionSwitch";
import { projectCopy } from "../projection/projectCopy";
import type { CopyKey } from "../projection/copyLexicon";
import { PERSONA_LABELS, type ExperiencePersona } from "../experience/types";
import { projectLabel } from "@/lib/spine/labels";
import { useExperience } from "../experience/ExperienceProvider";

type Props = {
  compact?: boolean;
  className?: string;
  /** Pin to top of shell — full width, always shows labels */
  prominent?: boolean;
};

const PERSONAS: ExperiencePersona[] = ["second-brain", "cognitive-lab"];

const PERSONA_ICONS = {
  "second-brain": Brain,
  "cognitive-lab": FlaskConical,
} as const;

const PERSONA_LABEL_KEYS: Record<ExperiencePersona, CopyKey> = {
  "second-brain": "personaSecondBrain",
  "cognitive-lab": "personaCognitiveLab",
};

export function ExperienceTierSwitch({ compact, className, prominent }: Props) {
  const theme = useMindTheme();
  const projection = useLanguageProjection();
  const lang = projection === "both" ? "zh" : projection;
  const { persona, setPersona } = useExperience();
  const showLabels = prominent || !compact;

  return (
    <div className={clsx("space-y-1", className)} data-cnexus-experience-switch>
      <div
        className={clsx(
          "inline-flex rounded-lg border p-0.5 gap-0.5",
          prominent ? "w-full max-w-md" : "w-full",
        )}
        style={{ borderColor: theme.border, backgroundColor: theme.surface }}
        role="tablist"
        aria-label={projectCopy("personaSwitchHint", "consumer", lang)}
      >
        {PERSONAS.map((p) => {
          const active = persona === p;
          const Icon = PERSONA_ICONS[p];
          const label = projectCopy(
            PERSONA_LABEL_KEYS[p],
            p === "second-brain" ? "consumer" : "research",
            lang,
          );
          return (
            <button
              key={p}
              type="button"
              role="tab"
              aria-selected={active}
              className={clsx(
                "flex flex-1 items-center justify-center gap-1.5 rounded-md font-medium transition",
                prominent ? "px-3 py-2 text-sm" : compact ? "px-2 py-1.5 text-[11px]" : "px-2 py-1.5 text-xs",
              )}
              style={{
                backgroundColor: active ? theme.sidebarActive : "transparent",
                color: active ? (p === "second-brain" ? "#5eead4" : theme.purple) : theme.textMuted,
                border: active ? `1px solid ${theme.border}` : "1px solid transparent",
              }}
              onClick={() => setPersona(p)}
              title={projectLabel(PERSONA_LABELS[p].subtitle, lang)}
            >
              <Icon className={clsx("shrink-0", prominent ? "w-4 h-4" : "w-3.5 h-3.5")} />
              {showLabels && <span className="truncate">{label}</span>}
            </button>
          );
        })}
      </div>
      {(prominent || !compact) && (
        <p className="text-[10px] leading-snug px-0.5" style={{ color: theme.textLight }}>
          {projectLabel(PERSONA_LABELS[persona].subtitle, lang)}
        </p>
      )}
    </div>
  );
}
