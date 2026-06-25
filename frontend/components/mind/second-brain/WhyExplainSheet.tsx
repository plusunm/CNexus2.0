"use client";

import type { CognitiveObject } from "@/lib/cognitive";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { projectProvenanceSource } from "@/lib/cognitive/projection/projectCopy";

type Props = {
  object: CognitiveObject;
  open: boolean;
  onClose: () => void;
  onOpenLab: (deepLink: string) => void;
};

export function WhyExplainSheet({ object, open, onClose, onOpenLab }: Props) {
  const t = useMindTheme();
  const { t: copy, dialect, lang } = useCognitiveCopy("creator");
  const provenance = object.provenance;

  if (!open || !provenance) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        aria-label="关闭"
        onClick={onClose}
      />
      <div
        className="relative w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl border p-5 space-y-4 shadow-xl"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div>
          <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: t.textLight }}>
            {copy("emergentInsight")}
          </p>
          <h3 className="text-base font-semibold leading-snug" style={{ color: t.text }}>
            {provenance.headline}
          </h3>
        </div>

        <div>
          <p className="text-xs font-medium mb-2" style={{ color: t.textMuted }}>
            {copy("provenanceHeadline")}
          </p>
          <ul className="space-y-2">
            {provenance.sources.map((source) => (
              <li key={source.kind} className="flex items-start gap-2 text-sm" style={{ color: t.text }}>
                <span style={{ color: t.green }}>✓</span>
                <span>{projectProvenanceSource(source.labelKey, source.count, dialect, lang)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 pt-1">
          <button
            type="button"
            className="flex-1 py-2.5 rounded-lg text-sm font-medium border"
            style={{ borderColor: t.border, color: t.textMuted }}
            onClick={onClose}
          >
            关闭
          </button>
          <button
            type="button"
            className="flex-1 py-2.5 rounded-lg text-sm font-medium"
            style={{ backgroundColor: t.purple, color: "#fff" }}
            onClick={() => {
              onOpenLab(provenance.labDeepLink);
              onClose();
            }}
          >
            {copy("openInLab")}
          </button>
        </div>
      </div>
    </div>
  );
}
