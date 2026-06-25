"use client";

import { useMemo } from "react";
import { useLanguageProjection } from "@/components/mind/LanguageProjectionSwitch";
import type { CognitiveObject } from "../objects/types";
import { ConflictObject, EmergenceObject } from "../objects/index";
import { projectCopy, projectObject, projectProvenanceSource } from "../projection/projectCopy";
import type { CopyKey, CognitiveDialect } from "../projection/copyLexicon";
import { useExperience } from "../experience/ExperienceProvider";

export function useCognitiveCopy(overrideDialect?: CognitiveDialect) {
  const { dialect: personaDialect } = useExperience();
  const projection = useLanguageProjection();
  const dialect = overrideDialect ?? personaDialect;
  const lang = projection === "both" ? "zh" : projection;

  return useMemo(
    () => ({
      dialect,
      lang,
      t: (key: CopyKey, vars?: Record<string, string | number>) => projectCopy(key, dialect, lang, vars),
      tObj: (obj: CognitiveObject) => projectObject(obj, dialect, lang),
      tSource: (labelKey: CopyKey, count: number) => projectProvenanceSource(labelKey, count, dialect, lang),
    }),
    [dialect, lang],
  );
}

export function useConflictCopy() {
  const base = useCognitiveCopy();
  return useMemo(() => ({ ...base, fromAudit: ConflictObject.fromAuditPair }), [base]);
}

export function useEmergenceCopy() {
  const base = useCognitiveCopy();
  return useMemo(
    () => ({
      ...base,
      fromInsight: EmergenceObject.fromInsight,
      fromDiscovery: EmergenceObject.fromDiscovery,
    }),
    [base],
  );
}
