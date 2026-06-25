import { biFmt, projectLabel, type BilingualLabel } from "@/lib/spine/labels";
import type { LanguageProjectionMode } from "@/lib/sibt/projectionMode";
import { cognitiveCopy, type CognitiveDialect, type CopyKey } from "./copyLexicon";
import type { CognitiveObject, ProjectedObject } from "../objects/types";

export function projectCopy(
  key: CopyKey,
  dialect: CognitiveDialect,
  lang: LanguageProjectionMode = "zh",
  vars?: Record<string, string | number>,
): string {
  const entry = cognitiveCopy[key][dialect];
  if (!vars || Object.keys(vars).length === 0) {
    return projectLabel(entry, lang);
  }
  return projectCopyFmt(entry, dialect, lang, vars);
}

export function projectCopyFmt(
  label: BilingualLabel,
  _dialect: CognitiveDialect,
  lang: LanguageProjectionMode,
  vars: Record<string, string | number>,
): string {
  if (lang === "both") return biFmt(label, vars);
  const single = lang === "en" ? label.en : label.zh;
  let out = single;
  for (const [key, val] of Object.entries(vars)) {
    out = out.split(`{${key}}`).join(String(val));
  }
  return out;
}

export function projectObject(
  obj: CognitiveObject,
  dialect: CognitiveDialect,
  lang: LanguageProjectionMode = "zh",
): ProjectedObject {
  return {
    title: projectCopy(obj.titleKey, dialect, lang),
    summary: obj.consumerSummary,
  };
}

export function projectProvenanceSource(
  labelKey: CopyKey,
  count: number,
  dialect: CognitiveDialect,
  lang: LanguageProjectionMode = "zh",
): string {
  return projectCopy(labelKey, dialect, lang, { count });
}
