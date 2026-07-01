/**
 * Cognitive Pipeline v1.5 — Event → Timeline → State → Canonical bridge.
 */

import type { RelationshipAnalysis } from "../types/relationship";
import { RELATIONSHIP_ANALYSIS_SCHEMA_VERSION } from "../types/relationship";
import type { ConversationTurn, EventStream } from "../events/eventOntology";
import { extractEventsFromConversation } from "../events/ruleBasedEventExtraction";
import { buildTimeline } from "../timeline/timelineBuilder";
import type { RelationshipTimeline } from "../timeline/timelineSchema";
import {
  dynamicsToCanonicalStage,
  metricsToLevelBands,
} from "../stateEngine/stateTransitionEngine";
import { routeModel } from "../ontology/modelRouter";
import { instantiateModelCard } from "../ontology/cardTemplateSystem";
import { runCausalEngineFromPipeline } from "../causal/causalEngine";
import type { CausalEngineResult } from "../causal/causalTypes";
import { runPredictionFromPipeline } from "../prediction/predictionEngine";
import type { PredictionResult } from "../prediction/predictionTypes";
import { runCounterfactualFromPipeline } from "../counterfactual/counterfactualEngine";
import type { CounterfactualEngineResult } from "../counterfactual/counterfactualTypes";

export type CognitivePipelineResult = {
  eventStream: EventStream;
  timeline: RelationshipTimeline;
  analysis: RelationshipAnalysis;
  sourceInput: string;
  causal: CausalEngineResult;
  prediction: PredictionResult;
  counterfactual: CounterfactualEngineResult;
};

function summarizeConversation(conversation: ConversationTurn[]): string {
  const last = conversation[conversation.length - 1];
  if (!last) return "关系聊天记录分析";
  const preview = last.text.length > 40 ? `${last.text.slice(0, 40)}…` : last.text;
  return `聊天记录分析：${preview}`;
}

function signalsFromTimeline(timeline: RelationshipTimeline): {
  positive: string[];
  negative: string[];
} {
  const last = timeline.segments[timeline.segments.length - 1];
  if (!last) return { positive: [], negative: [] };
  const m = last.metrics;
  const positive: string[] = [];
  const negative: string[] = [];
  if (m.initiativeRatio >= 0.4) positive.push("段内仍保持一定主动性");
  if (m.replyLatencyAvg < 1800 && m.messageCount >= 3) positive.push("回复延迟处于可接受范围");
  if (m.silenceRatio > 0.3) negative.push("沉默窗口占比偏高");
  if (m.replyLatencyAvg > 3600) negative.push("平均回复延迟显著增加");
  if (m.ignoreCount > 0) negative.push("存在未回应/长延迟互动");
  if (m.emotionColdCount > 0) negative.push("语气趋冷信号出现");
  if (!positive.length) positive.push("时间轴已结构化，可继续观察");
  return { positive, negative };
}

function decisionFromState(state: RelationshipTimeline["currentState"]): {
  recommended: "A" | "B" | "C" | "D";
  reason: string;
} {
  switch (state) {
    case "warm":
      return { recommended: "A", reason: "互动稳定，优先观察并收集更多信号" };
    case "neutral":
      return { recommended: "B", reason: "局面不确定，优先低压力沟通验证" };
    case "cold":
      return { recommended: "B", reason: "降温信号出现，宜验证而非猜测" };
    case "breaking":
      return { recommended: "C", reason: "崩解信号累积，宜降低投入并设边界" };
    case "broken":
      return { recommended: "D", reason: "长期低互动/无修复，宜做明确决策" };
  }
}

const OPTION_TEXT = {
  A: "等待观察 — 暂不行动，收集更多互动信号后再判断",
  B: "主动沟通验证 — 用低压力方式确认对方状态与意图",
  C: "降低投入 — 减少情绪消耗，保留边界与自我价值",
  D: "明确决策 — 在信息足够时做出继续或结束的清晰选择",
} as const;

export function runCognitivePipeline(
  conversation: ConversationTurn[],
  options?: { entities?: string[]; id?: string; sourceInput?: string },
): CognitivePipelineResult {
  const eventStream = extractEventsFromConversation(conversation, options?.entities);
  const timeline = buildTimeline(eventStream);
  const sourceInput = options?.sourceInput ?? summarizeConversation(conversation);
  const analysis = buildAnalysisFromTimeline(timeline, options, sourceInput);
  return enrichPipelineLayers({ eventStream, timeline, analysis, sourceInput });
}

/** Attach v2.1–v2.3 layers to event/timeline/analysis core (client or API hybrid). */
export function enrichPipelineLayers(input: {
  eventStream: EventStream;
  timeline: RelationshipTimeline;
  analysis: RelationshipAnalysis;
  sourceInput: string;
}): CognitivePipelineResult {
  const causal = runCausalEngineFromPipeline(input.eventStream, input.timeline);
  const prediction = runPredictionFromPipeline(input.timeline, causal);
  const counterfactual = runCounterfactualFromPipeline(prediction, causal);
  return {
    ...input,
    causal,
    prediction,
    counterfactual,
  };
}

function buildAnalysisFromTimeline(
  timeline: RelationshipTimeline,
  options: { entities?: string[]; id?: string; sourceInput?: string } | undefined,
  sourceInput: string,
): RelationshipAnalysis {
  const lastMetrics = timeline.segments[timeline.segments.length - 1]?.metrics;
  const bands = lastMetrics
    ? metricsToLevelBands(lastMetrics)
    : { emotionConnection: "medium" as const, initiativeLevel: "medium" as const, interactionFrequency: "low" as const };

  const sig = signalsFromTimeline(timeline);
  const dec = decisionFromState(timeline.currentState);

  return {
    meta: {
      id: options?.id ?? `tl-${Date.now()}`,
      sourceInput,
      createdAt: new Date().toISOString(),
      schemaVersion: RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
    },
    state: {
      ...bands,
      relationshipStage: dynamicsToCanonicalStage(timeline.currentState),
    },
    signals: sig,
    uncertainty: {
      missingInfo: timeline.segments.length < 2 ? ["时间轴段数较少，趋势判断有限"] : [],
      risk: timeline.currentState === "breaking" || timeline.currentState === "broken"
        ? "关系动力学显示衰退趋势，宜避免情绪驱动决策"
        : "基于行为时间轴推断，仍需结合线下事实验证",
    },
    decision: {
      options: { ...OPTION_TEXT },
      recommended: dec.recommended,
      reason: dec.reason,
    },
    actions: [
      `优先执行：${OPTION_TEXT[dec.recommended].split(" — ")[0]}`,
      "对照时间轴分段指标，记录后续 1–2 个窗口变化",
      "若沉默/ignore 信号持续，避免做不可逆决定",
    ],
  };
}

export function pipelineToModelCard(analysis: RelationshipAnalysis) {
  const route = routeModel(analysis);
  return instantiateModelCard(analysis, route);
}

/** Gateway timeline API when online; full client pipeline as fallback. */
export async function runTimelineAnalysisHybrid(
  conversation: ConversationTurn[],
  options?: { entities?: string[]; id?: string; sourceInput?: string },
): Promise<CognitivePipelineResult> {
  try {
    const { cnexusProductApi } = await import("@/lib/api");
    const data = await cnexusProductApi.analyzeRelationshipTimeline({
      conversation,
      entities:
        options?.entities && options.entities.length >= 2
          ? [options.entities[0], options.entities[1]]
          : undefined,
      sourceInput: options?.sourceInput,
      use_llm: true,
    });
    const eventStream = data.eventStream as EventStream | undefined;
    const timeline = data.timeline as RelationshipTimeline | undefined;
    if (!eventStream?.events || !timeline?.segments || !data.analysis) {
      throw new Error("incomplete timeline response");
    }
    return enrichPipelineLayers({
      eventStream,
      timeline,
      analysis: data.analysis,
      sourceInput: options?.sourceInput ?? data.analysis.meta.sourceInput,
    });
  } catch {
    return runCognitivePipeline(conversation, options);
  }
}
