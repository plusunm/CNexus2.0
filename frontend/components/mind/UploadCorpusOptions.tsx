"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { loadExpertSubjectId } from "@/lib/expertDistillMode";
import {
  EXPERT_DIMENSION_OPTIONS,
  fetchExpertSubjects,
  loadUploadCorpusMode,
  loadUploadExpertDimension,
  normalizeExpertSubjectId,
  saveUploadCorpusMode,
  saveUploadExpertDimension,
  type ExpertSemanticDimension,
  type UploadCorpusMode,
} from "@/lib/uploadCorpusOptions";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  corpus: UploadCorpusMode;
  onCorpusChange: (mode: UploadCorpusMode) => void;
  subjectId: string;
  onSubjectIdChange: (id: string) => void;
  semanticDimension: ExpertSemanticDimension;
  onSemanticDimensionChange: (dim: ExpertSemanticDimension) => void;
  compact?: boolean;
  className?: string;
};

export function useUploadCorpusState() {
  const [corpus, setCorpus] = useState<UploadCorpusMode>(() => loadUploadCorpusMode());
  const [subjectId, setSubjectId] = useState(() => loadExpertSubjectId());
  const [semanticDimension, setSemanticDimension] = useState<ExpertSemanticDimension>(() =>
    loadUploadExpertDimension(),
  );

  const setCorpusPersist = (mode: UploadCorpusMode) => {
    saveUploadCorpusMode(mode);
    setCorpus(mode);
  };

  const setSubjectPersist = (id: string) => {
    const normalized = normalizeExpertSubjectId(id);
    setSubjectId(normalized);
  };

  const setDimensionPersist = (dim: ExpertSemanticDimension) => {
    saveUploadExpertDimension(dim);
    setSemanticDimension(dim);
  };

  return {
    corpus,
    setCorpus: setCorpusPersist,
    subjectId,
    setSubjectId: setSubjectPersist,
    semanticDimension,
    setSemanticDimension: setDimensionPersist,
    ingestExpertFields: {
      corpus,
      subjectId,
      semanticDimension,
    },
  };
}

/** Upload target: general memory vs expert-tagged corpus for distill. */
export function UploadCorpusOptions({
  corpus,
  onCorpusChange,
  subjectId,
  onSubjectIdChange,
  semanticDimension,
  onSemanticDimensionChange,
  compact = false,
  className = "",
}: Props) {
  const t = useMindTheme();
  const [subjects, setSubjects] = useState<Array<{ subject_id: string }>>([]);

  useEffect(() => {
    if (corpus !== "expert") return;
    void fetchExpertSubjects().then((rows) => setSubjects(rows));
  }, [corpus]);

  const dimHint =
    EXPERT_DIMENSION_OPTIONS.find((opt) => opt.value === semanticDimension)?.hint ?? "";

  return (
    <div className={`space-y-2 ${className}`}>
      <div
        className={`flex gap-1 p-0.5 rounded-lg ${compact ? "text-[10px]" : "text-xs"}`}
        style={{ backgroundColor: t.chatBg }}
      >
        {(
          [
            { id: "general" as const, label: "通用记忆" },
            { id: "expert" as const, label: "专家语料" },
          ] as const
        ).map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => onCorpusChange(opt.id)}
            className={`flex-1 px-2.5 py-1 rounded-md font-medium transition-colors ${
              compact ? "py-0.5" : ""
            }`}
            style={{
              backgroundColor: corpus === opt.id ? (opt.id === "expert" ? "#14b8a622" : t.greenSoft) : "transparent",
              color: corpus === opt.id ? (opt.id === "expert" ? "#14b8a6" : t.green) : t.textMuted,
            }}
          >
            {opt.id === "expert" ? (
              <span className="inline-flex items-center justify-center gap-1">
                <Sparkles className="w-3 h-3 shrink-0" />
                {opt.label}
              </span>
            ) : (
              opt.label
            )}
          </button>
        ))}
      </div>

      {corpus === "expert" && (
        <div className={`grid gap-2 ${compact ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"}`}>
          <label className="flex flex-col gap-1 min-w-0">
            <span className={compact ? "text-[10px]" : "text-xs"} style={{ color: t.textMuted }}>
              专家主体 subject_id
            </span>
            <input
              list="cnexus-expert-subjects"
              className={`border rounded-lg px-2.5 outline-none ${compact ? "py-1 text-[11px]" : "py-1.5 text-xs"}`}
              style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
              value={subjectId}
              placeholder="expert:girlfriend"
              onChange={(e) => onSubjectIdChange(e.target.value)}
              onBlur={() => onSubjectIdChange(normalizeExpertSubjectId(subjectId))}
            />
            <datalist id="cnexus-expert-subjects">
              {subjects.map((row) => (
                <option key={row.subject_id} value={row.subject_id} />
              ))}
              <option value="expert:girlfriend" />
              <option value="expert:default" />
            </datalist>
          </label>
          <label className="flex flex-col gap-1 min-w-0">
            <span className={compact ? "text-[10px]" : "text-xs"} style={{ color: t.textMuted }}>
              语义维度
            </span>
            <select
              className={`border rounded-lg px-2.5 outline-none ${compact ? "py-1 text-[11px]" : "py-1.5 text-xs"}`}
              style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
              value={semanticDimension}
              onChange={(e) => onSemanticDimensionChange(e.target.value as ExpertSemanticDimension)}
            >
              {EXPERT_DIMENSION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          {dimHint ? (
            <p
              className={`${compact ? "text-[10px] col-span-full" : "text-[11px] col-span-full"}`}
              style={{ color: t.textMuted }}
            >
              导入后带专家标，可在 API 或后续面板执行 distill。{dimHint}
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
