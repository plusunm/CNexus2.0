"use client";

import { ExperienceTierSwitch } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";

/** Sticky experience persona bar — visible on all screen sizes. */
export function ExperiencePersonaBar() {
  const t = useMindTheme();

  return (
    <div
      className="shrink-0 px-4 py-2.5 border-b flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
      data-cnexus-persona-bar
    >
      <p className="text-[11px] font-medium" style={{ color: t.textMuted }}>
        使用方式
      </p>
      <ExperienceTierSwitch prominent className="w-full sm:max-w-[360px]" />
    </div>
  );
}
