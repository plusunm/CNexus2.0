"use client";

import { useCallback, useRef, useState } from "react";
import { GitBranch, Loader2, Save, Sparkles, Upload } from "lucide-react";
import { useMindTheme } from "../MindUiProvider";
import { SbSection, SbCard, SbEmptyState } from "./SbUIKit";
import { TimelinePage } from "./timeline/TimelinePage";
import { DecisionModelCardView } from "./thinking/DecisionModelCardView";
import {
  parseChatLog,
  runTimelineAnalysisHybrid,
  pipelineToModelCard,
  saveRelationshipCard,
  saveRelationshipMemory,
  buildMemoryRecord,
  type CognitivePipelineResult,
  type DecisionModelCard,
  type RelationshipAnalysisCard,
} from "@/lib/relationshipAnalysis";

const SAMPLE_CHAT = `2025-04-01 10:00 张三: 在干嘛
2025-04-01 10:05 李四: 刚下班，你呢
2025-04-01 10:10 张三: 周末一起吃饭？
2025-04-01 10:12 李四: 好啊，去哪
2025-04-02 14:00 张三: 人呢
2025-04-02 20:00 张三: 还在吗
2025-04-03 08:00 李四: 嗯
2025-04-05 09:00 张三: 最近还好吗
2025-04-08 11:00 李四: 忙`;

export function TimelineTab() {
  const t = useMindTheme();
  const fileRef = useRef<HTMLInputElement>(null);
  const [raw, setRaw] = useState("");
  const [entityA, setEntityA] = useState("");
  const [entityB, setEntityB] = useState("");
  const [title, setTitle] = useState("我的关系档案");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [result, setResult] = useState<CognitivePipelineResult | null>(null);
  const [participants, setParticipants] = useState<[string, string]>(["A", "B"]);
  const [card, setCard] = useState<DecisionModelCard | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [cardSaved, setCardSaved] = useState(false);

  const analyze = useCallback(() => {
    if (!raw.trim() || loading) return;
    setLoading(true);
    setError(null);
    setCard(null);
    setCardSaved(false);
    setSavedId(null);

    void (async () => {
      try {
        const parsed = parseChatLog(raw, {
          entityA: entityA.trim() || undefined,
          entityB: entityB.trim() || undefined,
        });
        setWarnings(parsed.warnings);
        if (parsed.turns.length === 0) {
          setError("未能解析任何消息，请检查格式");
          setResult(null);
          return;
        }

        const pipeline = await runTimelineAnalysisHybrid(parsed.turns, {
          entities: parsed.participants,
          sourceInput: title.trim() || `聊天分析 · ${parsed.turns.length} 条`,
        });
        setParticipants(parsed.participants);
        setResult(pipeline);
      } catch (e) {
        setError(e instanceof Error ? e.message : "分析失败");
        setResult(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [raw, entityA, entityB, title, loading]);

  const onFile = async (file: File | null) => {
    if (!file) return;
    const text = await file.text();
    setRaw(text);
    setWarnings([]);
  };

  const generateCard = () => {
    if (!result) return;
    const modelCard = pipelineToModelCard(result.analysis);
    setCard(modelCard);
    setCardSaved(false);
  };

  const saveArchive = () => {
    if (!result) return;
    const record = buildMemoryRecord({
      title: title.trim() || "关系档案",
      participants,
      eventStream: result.eventStream,
      timeline: result.timeline,
      relationshipState: result.timeline.currentState,
      analysis: result.analysis,
      card: card ?? undefined,
      causal: result.causal,
      prediction: result.prediction,
      counterfactual: result.counterfactual,
      id: savedId ?? undefined,
    });
    saveRelationshipMemory(record);
    setSavedId(record.id);
  };

  const saveCardToLibrary = () => {
    if (!result || !card) return;
    const envelope: RelationshipAnalysisCard = {
      ...result.analysis,
      card,
    };
    saveRelationshipCard(envelope);
    setCardSaved(true);
  };

  return (
    <div className="flex flex-col gap-5 pb-8 cnexus-float-scroll">
      <SbSection
        title="导入聊天记录"
        subtitle="微信导出 / txt / csv → 自动生成关系时间轴"
        icon={GitBranch}
      >
        <SbCard accent="teal" className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium" style={{ color: t.text }}>
              档案标题
            </span>
            <input
              className="input mt-2"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：和小王的聊天记录"
              disabled={loading}
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs" style={{ color: t.textMuted }}>
                参与者 A（可选）
              </span>
              <input
                className="input mt-1"
                value={entityA}
                onChange={(e) => setEntityA(e.target.value)}
                placeholder="张三 或 A"
                disabled={loading}
              />
            </label>
            <label className="block">
              <span className="text-xs" style={{ color: t.textMuted }}>
                参与者 B（可选）
              </span>
              <input
                className="input mt-1"
                value={entityB}
                onChange={(e) => setEntityB(e.target.value)}
                placeholder="李四 或 B"
                disabled={loading}
              />
            </label>
          </div>

          <label className="block">
            <span className="text-sm font-medium" style={{ color: t.text }}>
              聊天内容
            </span>
            <textarea
              className="input mt-2 min-h-[140px] resize-y font-mono text-xs"
              placeholder={`支持格式示例：\n2025-04-01 10:00 A: 在干嘛\n2025-04-01 10:05 B: 刚下班\n\n或微信两行格式：\n2025-04-01 10:00:00 张三\n消息内容`}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              disabled={loading}
            />
          </label>

          <div className="flex flex-wrap gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.csv,.log"
              className="hidden"
              onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              className="text-xs px-3 py-2 rounded-lg border flex items-center gap-1.5"
              style={{ borderColor: t.border, color: t.textMuted }}
              onClick={() => fileRef.current?.click()}
              disabled={loading}
            >
              <Upload className="w-3.5 h-3.5" />
              上传文件
            </button>
            <button
              type="button"
              className="text-xs px-3 py-2 rounded-lg border"
              style={{ borderColor: t.border, color: t.textMuted }}
              onClick={() => setRaw(SAMPLE_CHAT)}
              disabled={loading}
            >
              填入示例
            </button>
            <button
              type="button"
              className="btn text-xs ml-auto flex items-center gap-1.5"
              onClick={analyze}
              disabled={loading || !raw.trim()}
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitBranch className="w-3.5 h-3.5" />}
              生成时间轴
            </button>
          </div>

          {warnings.length > 0 && (
            <ul className="text-[11px] space-y-0.5" style={{ color: t.textMuted }}>
              {warnings.slice(0, 5).map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}
          {error && (
            <p className="text-xs" style={{ color: "#f472b6" }}>
              {error}
            </p>
          )}
        </SbCard>
      </SbSection>

      {!result && !loading && (
        <SbEmptyState>
          导入聊天，看见关系变化。粘贴或上传真实聊天记录，系统会自动提取事件、构建时间轴，并标注冷淡/升温等阶段变化。
        </SbEmptyState>
      )}

      {result && (
        <>
          <TimelinePage
            result={result}
            actions={
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="text-xs px-3 py-2 rounded-lg border flex items-center gap-1.5"
                  style={{ borderColor: t.border, color: t.textMuted }}
                  onClick={generateCard}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  生成模型卡
                </button>
                <button
                  type="button"
                  className="text-xs px-3 py-2 rounded-lg border flex items-center gap-1.5"
                  style={{ borderColor: t.border, color: t.textMuted }}
                  onClick={saveArchive}
                >
                  <Save className="w-3.5 h-3.5" />
                  {savedId ? "更新档案" : "保存关系档案"}
                </button>
              </div>
            }
          />

          {savedId && (
            <p className="text-[11px] px-1" style={{ color: "#5eead4" }}>
              已保存至本机记忆 · {savedId}
            </p>
          )}

          {card && (
            <SbSection title="决策模型卡">
              <DecisionModelCardView card={card} analysis={{ ...result.analysis, card }} />
              <div className="mt-3 flex gap-2">
                <button type="button" className="btn text-xs" onClick={saveCardToLibrary}>
                  {cardSaved ? "已加入模型库" : "保存到模型库"}
                </button>
              </div>
            </SbSection>
          )}
        </>
      )}
    </div>
  );
}
