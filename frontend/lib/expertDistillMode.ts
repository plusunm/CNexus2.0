import { getApiBase } from "./cnexusConfig";
import { notifyChatPrefsChanged } from "./chatPrefs";

/** Default subject when none registered yet — backend accepts expert:<id> profile. */
export const DEFAULT_EXPERT_SUBJECT = "expert:default";

const ENABLED_KEY = "cnexus-expert-distill-enabled";
const SUBJECT_KEY = "cnexus-expert-subject-id";

export type ExpertStyleSource = "prompt" | "recall" | "off";

export function loadExpertDistillEnabled(): boolean {
  try {
    return localStorage.getItem(ENABLED_KEY) === "1";
  } catch {
    return false;
  }
}

export function saveExpertDistillEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(ENABLED_KEY, enabled ? "1" : "0");
    notifyChatPrefsChanged();
  } catch {
    /* ignore */
  }
}

export function loadExpertSubjectId(): string {
  try {
    const value = localStorage.getItem(SUBJECT_KEY)?.trim();
    if (value) return value;
  } catch {
    /* ignore */
  }
  return DEFAULT_EXPERT_SUBJECT;
}

export function saveExpertSubjectId(subjectId: string): void {
  try {
    const sid = String(subjectId || "").trim() || DEFAULT_EXPERT_SUBJECT;
    localStorage.setItem(SUBJECT_KEY, sid);
    notifyChatPrefsChanged();
  } catch {
    /* ignore */
  }
}

export function expertDistillModeLabel(enabled: boolean): string {
  return enabled ? "蒸馏专家" : "通用模式";
}

/** Fields to merge into /api/converse POST body when expert distill is on. */
export function expertConverseFields(
  enabled?: boolean,
  subjectId?: string,
  styleSource: ExpertStyleSource = "prompt",
): Record<string, string> {
  const on = enabled === undefined ? loadExpertDistillEnabled() : enabled;
  if (!on) return {};
  const sid = String(subjectId || "").trim() || DEFAULT_EXPERT_SUBJECT;
  return {
    expert_mode: sid.startsWith("expert:") ? sid : `expert:${sid}`,
    expert_style_source: styleSource,
  };
}

/** Pick first registered subject from gateway, else default. */
export async function resolveExpertSubjectId(): Promise<string> {
  try {
    const resp = await fetch(`${getApiBase()}/api/expert/subjects`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) return loadExpertSubjectId();
    const data = (await resp.json()) as {
      ok?: boolean;
      subjects?: Array<{ subject_id?: string }>;
    };
    const first = data.subjects?.[0]?.subject_id?.trim();
    if (first) {
      saveExpertSubjectId(first);
      return first;
    }
  } catch {
    /* offline / expert API unavailable */
  }
  return loadExpertSubjectId();
}
