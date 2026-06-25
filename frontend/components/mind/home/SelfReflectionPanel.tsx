"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { bi, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

const DEFAULT_QUESTION =
  "根据最近 100 条 AuditLog，总结我这一周的认知偏差是什么？我是否有过度关注某些领域的倾向？";

export function SelfReflectionPanel() {
  const t = useMindTheme();
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [useLlm, setUseLlm] = useState(true);
  const [busy, setBusy] = useState(false);
  const [reflection, setReflection] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const row = await cnexusProductApi.runMetaReflection(question, useLlm);
      setReflection(String(row.reflection || ""));
      setSource(String(row.source || ""));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="rounded-xl border p-3 space-y-3"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex items-center gap-2">
        <Brain className="w-4 h-4" style={{ color: t.purple }} />
        <div>
          <p className="text-xs font-medium" style={{ color: t.text }}>
            {bi(navL.missionControlMetaReflection)}
          </p>
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            {bi(navL.missionControlMetaReflectionHint)}
          </p>
        </div>
      </div>

      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={3}
        className="w-full rounded-lg border px-2 py-1.5 text-xs"
        style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
      />

      <label className="flex items-center gap-2 text-[11px]" style={{ color: t.textMuted }}>
        <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
        {bi(navL.missionControlMetaReflectionLlm)}
      </label>

      <button
        type="button"
        disabled={busy || !question.trim()}
        onClick={() => void run()}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
        style={{ borderColor: t.border, color: t.text }}
      >
        {busy ? "…" : bi(navL.missionControlMetaReflectionRun)}
      </button>

      {reflection && (
        <div
          className="rounded-lg border p-2 text-[11px] whitespace-pre-wrap max-h-48 overflow-y-auto"
          style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.textMuted }}
        >
          {source && (
            <p className="text-[10px] mb-1" style={{ color: t.textLight }}>
              {bi(navL.missionControlMetaReflectionSource)}: {source}
            </p>
          )}
          {reflection}
        </div>
      )}

      {error && (
        <p className="text-[11px]" style={{ color: t.orange }}>
          {error}
        </p>
      )}
    </section>
  );
}
