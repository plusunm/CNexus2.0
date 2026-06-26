"use client";

import { ExperienceTierSwitch, useExperience } from "@/lib/cognitive";
import { PERSONA_LABELS } from "@/lib/cognitive/experience/types";
import { projectLabel } from "@/lib/spine/labels";
import { useLanguageProjection } from "./LanguageProjectionSwitch";
import { useMindTheme } from "./MindUiProvider";

/** Sticky experience persona bar — mobile / tablet; desktop uses sidebar switch. */
export function ExperiencePersonaBar() {
  const t = useMindTheme();
  const projection = useLanguageProjection();
  const lang = projection === "both" ? "zh" : projection;
  const { persona } = useExperience();

  return (
    <div
      className="shrink-0 px-4 py-2.5 border-b lg:hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
      data-cnexus-persona-bar
    >
      <div className="flex items-center gap-3">
        <p className="text-[11px] font-medium shrink-0" style={{ color: t.textMuted }}>
          使用方式
        </p>
        <ExperienceTierSwitch prominent showHint={false} className="flex-1 min-w-0 max-w-[360px]" />
      </div>
      <p className="text-[10px] leading-snug mt-2 px-0.5" style={{ color: t.textLight }}>
        {projectLabel(PERSONA_LABELS[persona].subtitle, lang)}
      </p>
    </div>
  );
}
