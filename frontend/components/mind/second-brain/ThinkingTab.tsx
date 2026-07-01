"use client";

import { useMemo, useState } from "react";
import { Brain, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { useMindTheme } from "../MindUiProvider";
import { useRelationshipAnalysis } from "@/hooks/useRelationshipAnalysis";
import { decisionExamplesByDomain } from "@/lib/relationshipAnalysis";
import { SbSection, SbCard, SbEmptyState } from "./SbUIKit";
import { RelationshipAnalysisView } from "./thinking/RelationshipAnalysisView";
import { ThinkingDomainNav } from "./thinking/ThinkingDomainNav";
import {
  THINKING_DOMAIN_COLORS,
  THINKING_DOMAIN_META,
  type DecisionExampleDomain,
} from "./thinking/thinkingDomains";

export function ThinkingTab() {
  const t = useMindTheme();
  const { result, loading, error, warning, analyze, reset } = useRelationshipAnalysis();
  const [domain, setDomain] = useState<DecisionExampleDomain>("恋爱");
  const [input, setInput] = useState("");
  const [examplesOpen, setExamplesOpen] = useState(false);
  const examplesByDomain = useMemo(() => decisionExamplesByDomain(), []);
  const domainMeta = THINKING_DOMAIN_META[domain];
  const domainExamples = examplesByDomain[domain];
  const domainColor = THINKING_DOMAIN_COLORS[domain];

  const pickExample = (text: string) => {
    setInput(text);
    setExamplesOpen(false);
  };

  const submit = () => {
    if (!input.trim() || loading) return;
    void analyze(input);
  };

  return (
    <div className="flex flex-col gap-5 pb-8 cnexus-float-scroll">
      <ThinkingDomainNav
        value={domain}
        onChange={(next) => {
          setDomain(next);
          setExamplesOpen(false);
        }}
        disabled={loading}
      />

      <SbSection
        title={domainMeta.title}
        subtitle={domainMeta.subtitle}
        icon={Brain}
      >
        <SbCard accent="teal" className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium" style={{ color: t.text }}>
              你现在要分析什么决策问题？
            </span>
            <textarea
              className="input mt-2 min-h-[96px] resize-y"
              placeholder={domainMeta.placeholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
              }}
              disabled={loading}
            />
          </label>

          {domainExamples.length > 0 && (
            <div
              className="rounded-xl border overflow-hidden"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <button
                type="button"
                className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left"
                onClick={() => setExamplesOpen((v) => !v)}
                aria-expanded={examplesOpen}
                disabled={loading}
              >
                <div className="min-w-0">
                  <span className="text-xs font-medium" style={{ color: t.text }}>
                    选择{domain}示例
                  </span>
                  {!examplesOpen && (
                    <p className="text-[10px] mt-0.5 truncate" style={{ color: t.textMuted }}>
                      {domainExamples.map((row) => row.direction).join(" · ")}
                    </p>
                  )}
                </div>
                {examplesOpen ? (
                  <ChevronUp className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
                ) : (
                  <ChevronDown className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
                )}
              </button>

              {examplesOpen && (
                <div
                  className="px-3 pb-3 pt-1 flex flex-col gap-1.5 border-t max-h-[240px] overflow-y-auto cnexus-float-scroll"
                  style={{ borderColor: t.border }}
                >
                  {domainExamples.map((sample) => (
                    <button
                      key={sample.id}
                      type="button"
                      className="text-xs px-2.5 py-2 rounded-lg border transition hover:opacity-90 text-left w-full"
                      style={{
                        borderColor: t.border,
                        color: t.textMuted,
                        backgroundColor: t.surface,
                      }}
                      onClick={() => pickExample(sample.text)}
                      disabled={loading}
                      title={sample.direction}
                    >
                      <span
                        className="mr-1.5 px-1 py-0.5 rounded text-[10px] inline-block"
                        style={{
                          backgroundColor: `${domainColor}22`,
                          color: domainColor,
                        }}
                      >
                        {sample.direction}
                      </span>
                      {sample.text}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center gap-2">
            <button type="button" className="btn" onClick={submit} disabled={loading || !input.trim()}>
              {loading ? (
                <>
                  <Loader2 className="inline w-4 h-4 mr-1.5 animate-spin" />
                  深度思考中…
                </>
              ) : (
                "开始思考"
              )}
            </button>
            {result && (
              <button
                type="button"
                className="text-xs px-3 py-2 rounded-lg border"
                style={{ borderColor: t.border, color: t.textMuted }}
                onClick={() => {
                  reset();
                  setInput("");
                }}
              >
                清空
              </button>
            )}
          </div>

          {warning && (
            <p className="text-xs" style={{ color: "#FAAD14" }}>
              {warning}
            </p>
          )}

          {error && (
            <p className="text-xs" style={{ color: "#FF4D4F" }}>
              {error}
            </p>
          )}
        </SbCard>
      </SbSection>

      {result ? (
        <RelationshipAnalysisView data={result} />
      ) : (
        !loading && (
          <SbEmptyState>
            输入{domain}相关决策问题后，系统将按固定结构展示：当前状态、信号、不确定性与决策路径。
          </SbEmptyState>
        )
      )}
    </div>
  );
}
