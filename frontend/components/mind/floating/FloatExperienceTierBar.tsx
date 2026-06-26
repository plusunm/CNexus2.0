"use client";

import { Brain, ExternalLink, FlaskConical } from "lucide-react";
import clsx from "clsx";
import { useMindTheme } from "../MindUiProvider";
import { useLanguageProjection } from "../LanguageProjectionSwitch";
import { projectCopy } from "@/lib/cognitive/projection/projectCopy";
import { projectLabel } from "@/lib/spine/labels";
import { PERSONA_LABELS } from "@/lib/cognitive/experience/types";
import { isFloatPersonalEdition, personalLabUiUrl, personalMainUiUrl } from "@/lib/floatPersonal";
import { isTauriDesktop, openTauriDashboard } from "@/lib/tauriDesktop";

/** Float expand header — open Second Brain / Cognitive Lab in full dashboard windows. */
export function FloatExperienceTierBar() {
  const theme = useMindTheme();
  const projection = useLanguageProjection();
  const lang = projection === "both" ? "zh" : projection;

  const openMainWindow = () => {
    const route = isFloatPersonalEdition() ? "/" : "/shell?layout=overview";
    if (isTauriDesktop()) {
      void openTauriDashboard(route);
      return;
    }
    const url = isFloatPersonalEdition() ? personalMainUiUrl() : `${window.location.origin}${route}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const openLabWindow = () => {
    const route = personalLabUiUrl();
    if (isTauriDesktop()) {
      void openTauriDashboard(route);
      return;
    }
    window.open(`${window.location.origin}${route}`, "_blank", "noopener,noreferrer");
  };

  const sectionLabel = projectCopy("floatOpenBigWindowSection", "consumer", lang);
  const secondBigWindowLabel = projectCopy("floatSecondBrainBigWindow", "consumer", lang);
  const labBigWindowLabel = projectCopy("floatCognitiveLabBigWindow", "research", lang);
  const footnote = projectCopy("floatBigWindowFootnote", "consumer", lang);

  const bigWindowButtonClass =
    "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] font-medium transition opacity-90 hover:opacity-100";

  return (
    <div className="space-y-1" data-cnexus-experience-switch>
      <p className="text-[10px] font-medium px-0.5" style={{ color: theme.textMuted }}>
        {sectionLabel}
      </p>
      <div
        className="inline-flex w-full rounded-lg border p-0.5 gap-0.5"
        style={{ borderColor: theme.border, backgroundColor: theme.surface }}
        role="group"
        aria-label={sectionLabel}
      >
        <button
          type="button"
          className={clsx(bigWindowButtonClass)}
          style={{
            backgroundColor: "transparent",
            color: "#5eead4",
            border: `1px solid ${theme.border}`,
          }}
          title={projectLabel(PERSONA_LABELS["second-brain"].subtitle, lang)}
          onClick={openMainWindow}
        >
          <Brain className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{secondBigWindowLabel}</span>
          <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
        </button>
        <button
          type="button"
          className={clsx(bigWindowButtonClass)}
          style={{
            backgroundColor: "transparent",
            color: theme.purple,
            border: `1px solid ${theme.border}`,
          }}
          title={projectLabel(PERSONA_LABELS["cognitive-lab"].subtitle, lang)}
          onClick={openLabWindow}
        >
          <FlaskConical className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{labBigWindowLabel}</span>
          <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
        </button>
      </div>
      <p className="text-[10px] leading-snug px-0.5" style={{ color: theme.textLight }}>
        {footnote}
      </p>
    </div>
  );
}
