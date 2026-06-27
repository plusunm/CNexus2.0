import {
  DEFAULT_EXPERT_SUBJECT,
  loadExpertSubjectId,
  saveExpertSubjectId,
} from "./expertDistillMode";
import { getApiBase } from "./cnexusConfig";

export type UploadCorpusMode = "general" | "expert";

export type ExpertSemanticDimension = "style" | "decision" | "fact";

export const EXPERT_DIMENSION_OPTIONS: Array<{
  value: ExpertSemanticDimension;
  label: string;
  hint: string;
}> = [
  { value: "style", label: "风格 style", hint: "聊天语气、表达习惯（推荐）" },
  { value: "decision", label: "决策 decision", hint: "偏好与选择模式" },
  { value: "fact", label: "事实 fact", hint: "客观信息，建议后续 fact-confirm" },
];

const CORPUS_KEY = "cnexus-upload-corpus-mode";
const DIMENSION_KEY = "cnexus-upload-expert-dimension";

export function loadUploadCorpusMode(): UploadCorpusMode {
  try {
    const value = localStorage.getItem(CORPUS_KEY);
    if (value === "expert") return "expert";
  } catch {
    /* ignore */
  }
  return "general";
}

export function saveUploadCorpusMode(mode: UploadCorpusMode): void {
  try {
    localStorage.setItem(CORPUS_KEY, mode);
  } catch {
    /* ignore */
  }
}

export function loadUploadExpertDimension(): ExpertSemanticDimension {
  try {
    const value = localStorage.getItem(DIMENSION_KEY)?.trim().toLowerCase();
    if (value === "style" || value === "decision" || value === "fact") return value;
  } catch {
    /* ignore */
  }
  return "style";
}

export function saveUploadExpertDimension(dimension: ExpertSemanticDimension): void {
  try {
    localStorage.setItem(DIMENSION_KEY, dimension);
  } catch {
    /* ignore */
  }
}

/** Ensure expert:<id> prefix for gateway policy / capture API. */
export function normalizeExpertSubjectId(subjectId?: string): string {
  const raw = String(subjectId || "").trim() || loadExpertSubjectId() || DEFAULT_EXPERT_SUBJECT;
  if (raw.startsWith("expert:")) return raw;
  return `expert:${raw.replace(/^expert:/, "")}`;
}

export type IngestExpertFields = {
  corpus?: UploadCorpusMode;
  subjectId?: string;
  semanticDimension?: ExpertSemanticDimension;
};

/** Fields merged into gateway ingest policy or multipart form when corpus=expert. */
export function buildExpertIngestFields(
  opts: IngestExpertFields,
): Record<string, string> | undefined {
  if (opts.corpus !== "expert") return undefined;
  const sid = normalizeExpertSubjectId(opts.subjectId);
  saveExpertSubjectId(sid);
  return {
    subject_id: sid,
    semantic_dimension: opts.semanticDimension ?? loadUploadExpertDimension(),
    distill_mode: "ingest",
  };
}

export type ExpertSubjectRow = { subject_id: string; block_count?: number };

/** Registered expert subjects for upload picker. */
export async function fetchExpertSubjects(): Promise<ExpertSubjectRow[]> {
  try {
    const resp = await fetch(`${getApiBase()}/api/expert/subjects`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) return [];
    const data = (await resp.json()) as {
      ok?: boolean;
      subjects?: Array<{ subject_id?: string; block_count?: number }>;
    };
    return (data.subjects ?? [])
      .map((row) => ({
        subject_id: String(row.subject_id || "").trim(),
        block_count: row.block_count,
      }))
      .filter((row) => row.subject_id.length > 0);
  } catch {
    return [];
  }
}
