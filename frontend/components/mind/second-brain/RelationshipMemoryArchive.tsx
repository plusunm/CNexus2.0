"use client";

import { useCallback, useEffect, useState } from "react";
import { GitBranch, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import {
  listRelationshipMemories,
  deleteRelationshipMemory,
  RELATIONSHIP_MEMORY_STORE_KEY,
  DYNAMICS_STATE_LABELS,
  type RelationshipMemoryRecord,
  type CognitivePipelineResult,
  runCausalEngineFromPipeline,
  runPredictionFromPipeline,
  runCounterfactualFromPipeline,
} from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../MindUiProvider";
import { SbSection, SbCard, SbEmptyState } from "./SbUIKit";
import { TimelinePage } from "./timeline/TimelinePage";
import { DecisionModelCardView } from "./thinking/DecisionModelCardView";

function toPipelineResult(record: RelationshipMemoryRecord): CognitivePipelineResult | null {
  if (!record.analysis) return null;
  const causal =
    record.causal ?? runCausalEngineFromPipeline(record.eventStream, record.timeline);
  const prediction =
    record.prediction ?? runPredictionFromPipeline(record.timeline, causal);
  const counterfactual =
    record.counterfactual ?? runCounterfactualFromPipeline(prediction, causal);
  return {
    eventStream: record.eventStream,
    timeline: record.timeline,
    analysis: record.analysis,
    sourceInput: record.analysis.meta.sourceInput,
    causal,
    prediction,
    counterfactual,
  };
}

function fmtDate(ts: number): string {
  try {
    return new Date(ts).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(ts);
  }
}

export function RelationshipMemoryArchive() {
  const t = useMindTheme();
  const [records, setRecords] = useState<RelationshipMemoryRecord[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setRecords(listRelationshipMemories());
  }, []);

  useEffect(() => {
    refresh();
    const onStorage = (e: StorageEvent) => {
      if (e.key === RELATIONSHIP_MEMORY_STORE_KEY) refresh();
    };
    const onLocal = () => refresh();
    window.addEventListener("storage", onStorage);
    window.addEventListener("cnexus-relationship-memory-updated", onLocal);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("cnexus-relationship-memory-updated", onLocal);
    };
  }, [refresh]);

  const onDelete = (id: string) => {
    deleteRelationshipMemory(id);
    if (expandedId === id) setExpandedId(null);
    refresh();
  };

  return (
    <SbSection
      title="关系档案"
      subtitle="从「关系时间轴」保存的聊天分析，可在此回放阶段变化与模型卡。"
      icon={GitBranch}
    >
      {records.length === 0 ? (
        <SbEmptyState>
          还没有关系档案。在「关系时间轴」导入聊天并点击「保存关系档案」后，会出现在这里。
        </SbEmptyState>
      ) : (
        <ul className="space-y-2">
          {records.map((record) => {
            const open = expandedId === record.id;
            const pipeline = toPipelineResult(record);
            return (
              <li key={record.id}>
                <SbCard padding="sm" accent="teal" className="space-y-0">
                  <div className="flex items-start justify-between gap-2">
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => setExpandedId(open ? null : record.id)}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium" style={{ color: t.text }}>
                          {record.title}
                        </p>
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full border"
                          style={{ borderColor: "#5eead455", color: "#5eead4", backgroundColor: "#5eead414" }}
                        >
                          {DYNAMICS_STATE_LABELS[record.relationshipState]}
                        </span>
                      </div>
                      <p className="text-[11px] mt-1" style={{ color: t.textMuted }}>
                        {record.participants.join(" ↔ ")} · {record.timeline.segments.length} 段 · 更新于{" "}
                        {fmtDate(record.updatedAt)}
                      </p>
                    </button>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        className="p-1.5 rounded-lg border"
                        style={{ borderColor: t.border, color: t.textMuted }}
                        onClick={() => setExpandedId(open ? null : record.id)}
                        aria-label={open ? "收起" : "展开"}
                      >
                        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      <button
                        type="button"
                        className="p-1.5 rounded-lg border"
                        style={{ borderColor: "#f472b655", color: "#f472b6" }}
                        onClick={() => onDelete(record.id)}
                        aria-label="删除档案"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {open && pipeline && (
                    <div className="mt-4 pt-4 border-t space-y-4" style={{ borderColor: t.border }}>
                      <TimelinePage result={pipeline} />
                      {record.card && record.analysis && (
                        <DecisionModelCardView card={record.card} analysis={{ ...record.analysis, card: record.card }} />
                      )}
                    </div>
                  )}
                  {open && !pipeline && (
                    <p className="text-xs mt-3 pt-3 border-t" style={{ borderColor: t.border, color: t.textMuted }}>
                      档案数据不完整，无法回放时间轴。
                    </p>
                  )}
                </SbCard>
              </li>
            );
          })}
        </ul>
      )}
    </SbSection>
  );
}
