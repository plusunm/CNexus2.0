/**
 * Offline / legacy fallback adapter — maps backend JSON → canonical SSOT.
 * Primary path: POST /api/analyze (server-side canonical output).
 */

import { assertRelationshipAnalysis } from "./assertCanonical";
import type { ConverseBlockingRaw, StatusRaw } from "./converseRaw";
import {
  DECISION_OPTION_IDS,
  RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
  type DecisionOptionId,
  type LevelBand,
  type RelationshipAnalysis,
  type RelationshipAnalysisCard,
  type RelationshipStage,
} from "./types/relationship";

const DECISION_OPTION_TEXT: Record<DecisionOptionId, string> = {
  A: "等待观察 — 暂不行动，收集更多互动信号后再判断",
  B: "主动沟通验证 — 用低压力方式确认对方状态与意图",
  C: "降低投入 — 减少情绪消耗，保留边界与自我价值",
  D: "明确决策 — 在信息足够时做出继续或结束的清晰选择",
};

const RISK_BY_STAGE: Record<RelationshipStage, string> = {
  stable: "整体风险偏低，但仍需避免过度解读单次互动",
  cold: "冷淡信号持续可能放大误解，宜尽快验证而非猜测",
  uncertain: "信息不足时贸然行动容易误判，优先补齐关键事实",
  broken: "信任与情绪双低，继续拖延可能增加情绪消耗",
};

function emotionValence(raw?: ConverseBlockingRaw["emotion"]): number {
  if (!raw) return 0;
  return Number(raw.valence ?? raw.val ?? 0);
}

function relationshipTrust(converse: ConverseBlockingRaw, status?: StatusRaw): number {
  const rel = converse.relationship ?? status?.relationship;
  if (!rel) return 0.5;
  if (typeof rel.trust === "number") return rel.trust;
  if (typeof rel.closeness === "number") return rel.closeness;
  if (typeof rel.tone === "number") return (rel.tone + 1) / 2;
  return 0.5;
}

function mapState(converse: ConverseBlockingRaw, status?: StatusRaw): RelationshipAnalysis["state"] {
  const valence = emotionValence(converse.emotion ?? status?.emotion);
  const arousal = Number(converse.emotion?.arousal ?? status?.emotion?.arousal ?? 0.5);
  const trust = relationshipTrust(converse, status);
  const recall = Number(converse.cog_state?.recall_strength ?? 0.5);
  const hits = converse.activation_injected ?? converse.activation_hits?.length ?? 0;

  const emotionConnection: LevelBand =
    valence < -0.25 ? "low" : valence > 0.25 ? "high" : "medium";
  const initiativeLevel: LevelBand =
    arousal < 0.35 || recall < 0.4 ? "low" : recall > 0.65 || arousal > 0.65 ? "high" : "medium";
  const interactionFrequency: LevelBand = hits === 0 ? "low" : hits >= 3 ? "high" : "medium";

  let relationshipStage: RelationshipStage = "uncertain";
  if (trust < 0.35 && valence < -0.2) relationshipStage = "broken";
  else if (valence < -0.2 || interactionFrequency === "low") relationshipStage = "cold";
  else if (trust >= 0.55 && emotionConnection !== "low") relationshipStage = "stable";

  return { emotionConnection, initiativeLevel, interactionFrequency, relationshipStage };
}

function mapSignals(converse: ConverseBlockingRaw, sourceInput: string): RelationshipAnalysis["signals"] {
  const positive: string[] = [];
  const negative: string[] = [];

  for (const hit of converse.activation_hits ?? []) {
    const title = (hit.title ?? "").trim();
    if (!title) continue;
    if ((hit.score ?? 0) >= 0.45) positive.push(title);
    else negative.push(title);
  }

  const valence = emotionValence(converse.emotion);
  if (valence > 0.2) positive.push("当前情绪基调偏正向");
  else if (valence < -0.2) negative.push("当前情绪基调偏负向");

  const intent = (converse.intent ?? converse.cog_state?.active_intent ?? "").toLowerCase();
  if (intent.includes("recall") || intent.includes("memory")) positive.push("系统召回了相关历史记忆");
  if (positive.length === 0) positive.push("问题已纳入结构化分析框架");
  if (negative.length === 0 && /不理|冷淡|分手|消失|不回/.test(sourceInput)) {
    negative.push("输入描述暗示互动减少或回应延迟");
  }
  if (negative.length === 0 && /甩锅|抢功|压榨|领导|老板|上级/.test(sourceInput)) {
    negative.push("输入描述暗示职场关系存在压力或不公平");
  }
  if (negative.length === 0 && /跳槽|offer|裸辞|求职|面试|辞职/.test(sourceInput)) {
    negative.push("输入描述暗示职业选择存在机会与风险并存");
  }

  return { positive: positive.slice(0, 6), negative: negative.slice(0, 6) };
}

function mapUncertainty(
  converse: ConverseBlockingRaw,
  state: RelationshipAnalysis["state"],
): RelationshipAnalysis["uncertainty"] {
  const missingInfo: string[] = [];
  const hits = converse.activation_injected ?? 0;
  const ctx = (converse.activation_context ?? "").trim();

  if (hits === 0) missingInfo.push("缺少可召回的相关历史记忆");
  if (!ctx) missingInfo.push("缺少关键事实或对方立场描述");
  if (!converse.relationship && !converse.emotion) missingInfo.push("局面快照信息不完整");
  if (missingInfo.length === 0) missingInfo.push("部分推断基于有限上下文，需后续验证");

  return { missingInfo: missingInfo.slice(0, 4), risk: RISK_BY_STAGE[state.relationshipStage] };
}

function mapDecision(
  converse: ConverseBlockingRaw,
  status: StatusRaw | undefined,
  sourceInput: string,
): RelationshipAnalysis["decision"] {
  const trust = relationshipTrust(converse, status);
  const valence = emotionValence(converse.emotion ?? status?.emotion);
  const hits = converse.activation_injected ?? 0;

  let recommended: DecisionOptionId = "A";
  let reason = "信号尚不充分，先观察再行动风险更低";

  if (/分手|结束|离开|裸辞|立刻辞职/.test(sourceInput) && (trust < 0.4 || /裸辞|立刻辞职/.test(sourceInput))) {
    recommended = "D";
    reason = "问题指向重大去留，适合先做明确决策而非拖延";
  } else if (/跳槽|offer|加薪|老板|领导|上级|甩锅/.test(sourceInput)) {
    recommended = "B";
    reason = "职场/求职类问题宜先沟通或核实关键信息再行动";
  } else if (hits === 0 || trust < 0.45) {
    recommended = "B";
    reason = "信息不足，优先通过沟通或调研验证假设";
  } else if (valence < -0.3) {
    recommended = "C";
    reason = "局面偏冷或消耗偏高，建议先降低投入、保护边界";
  } else if (/暧昧|推进|表白/.test(sourceInput)) {
    recommended = "B";
    reason = "关系推进类问题适合小步验证，避免过度解读";
  }

  const options = Object.fromEntries(
    DECISION_OPTION_IDS.map((id) => [id, DECISION_OPTION_TEXT[id]]),
  ) as Record<DecisionOptionId, string>;

  return { options, recommended, reason };
}

import { ruleBasedModelCard } from "./modelCardCoerce";

export function backendToCanonical(
  sourceInput: string,
  converse: ConverseBlockingRaw,
  status?: StatusRaw,
  id?: string,
): RelationshipAnalysis {
  const trimmed = sourceInput.trim();
  const state = mapState(converse, status);
  const decision = mapDecision(converse, status, trimmed);
  const primary = decision.options[decision.recommended];

  const analysis: RelationshipAnalysis = {
    meta: {
      id: id ?? `ra-${Date.now()}`,
      sourceInput: trimmed,
      createdAt: new Date().toISOString(),
      schemaVersion: RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
    },
    state,
    signals: mapSignals(converse, trimmed),
    uncertainty: mapUncertainty(converse, state),
    decision,
    actions: [
      `优先执行：${primary}`,
      "记录后续 1–2 次关键反馈，用于更新判断",
      "若不确定性项未消除，避免做不可逆决定",
    ],
  };

  assertRelationshipAnalysis(analysis);
  return analysis;
}

export function toRelationshipCard(analysis: RelationshipAnalysis): RelationshipAnalysisCard {
  assertRelationshipAnalysis(analysis);
  return {
    ...analysis,
    card: ruleBasedModelCard(analysis),
  };
}

/** @deprecated use backendToCanonical */
export const mapBackendToRelationshipAnalysis = backendToCanonical;
