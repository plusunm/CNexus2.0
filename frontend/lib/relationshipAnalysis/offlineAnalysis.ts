/**
 * Offline fallback — Thinking tab when gateway is unreachable.
 */

import {
  DECISION_OPTION_IDS,
  RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
  type DecisionOptionId,
  type LevelBand,
  type RelationshipAnalysis,
  type RelationshipStage,
} from "./types/relationship";

const OPTION_TEXT: Record<DecisionOptionId, string> = {
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

function inferStage(text: string): RelationshipStage {
  if (/分手|结束|离开|拉黑|彻底/.test(text)) return "broken";
  if (/冷淡|不理|消失|不回|疏远|冷战/.test(text)) return "cold";
  if (/稳定|顺利|很好|推进/.test(text)) return "stable";
  return "uncertain";
}

function inferDecision(text: string): { recommended: DecisionOptionId; reason: string } {
  if (/分手|结束|离开|裸辞|立刻辞职/.test(text)) {
    return { recommended: "D", reason: "问题指向重大去留，适合先做明确决策而非拖延" };
  }
  if (/跳槽|offer|加薪|老板|领导|上级|甩锅|职称|同事|职场|面试/.test(text)) {
    return { recommended: "B", reason: "职场/求职类问题宜先沟通或核实关键信息再行动" };
  }
  if (/冷淡|不理|消失|不回/.test(text)) {
    return { recommended: "B", reason: "信息不足或互动降温，优先低压力验证而非猜测" };
  }
  if (/暧昧|推进|表白/.test(text)) {
    return { recommended: "B", reason: "关系推进类问题适合小步验证，避免过度解读" };
  }
  return { recommended: "A", reason: "信号尚不充分，先观察再行动风险更低" };
}

function inferSignals(text: string): RelationshipAnalysis["signals"] {
  const positive: string[] = [];
  const negative: string[] = [];

  if (/还好|愿意|主动|推进|暧昧|喜欢/.test(text)) positive.push("描述中存在正向互动或意愿信号");
  if (/不理|冷淡|分手|消失|不回/.test(text)) negative.push("描述暗示互动减少或回应延迟");
  if (/甩锅|抢功|压榨|不公平|职称|竞争/.test(text)) negative.push("描述暗示职场关系存在压力或不公平");
  if (/跳槽|offer|裸辞|求职|面试|辞职/.test(text)) negative.push("描述暗示职业选择存在机会与风险并存");

  if (!positive.length) positive.push("问题已纳入结构化分析框架（离线规则）");
  return { positive: positive.slice(0, 6), negative: negative.slice(0, 6) };
}

function bandsForStage(stage: RelationshipStage): {
  emotionConnection: LevelBand;
  initiativeLevel: LevelBand;
  interactionFrequency: LevelBand;
} {
  if (stage === "stable") {
    return { emotionConnection: "high", initiativeLevel: "medium", interactionFrequency: "medium" };
  }
  if (stage === "cold" || stage === "broken") {
    return { emotionConnection: "low", initiativeLevel: "low", interactionFrequency: "low" };
  }
  return { emotionConnection: "medium", initiativeLevel: "medium", interactionFrequency: "low" };
}

export function buildOfflineRelationshipAnalysis(
  sourceInput: string,
  options?: { id?: string },
): RelationshipAnalysis {
  const trimmed = sourceInput.trim();
  const stage = inferStage(trimmed);
  const decision = inferDecision(trimmed);
  const bands = bandsForStage(stage);

  return {
    meta: {
      id: options?.id ?? `offline-${Date.now()}`,
      sourceInput: trimmed,
      createdAt: new Date().toISOString(),
      schemaVersion: RELATIONSHIP_ANALYSIS_SCHEMA_VERSION,
    },
    state: { ...bands, relationshipStage: stage },
    signals: inferSignals(trimmed),
    uncertainty: {
      missingInfo: [
        "当前为离线规则分析，未连接本机网关",
        "缺少对方立场与历史互动细节",
      ],
      risk: RISK_BY_STAGE[stage],
    },
    decision: {
      options: Object.fromEntries(DECISION_OPTION_IDS.map((id) => [id, OPTION_TEXT[id]])) as Record<
        DecisionOptionId,
        string
      >,
      recommended: decision.recommended,
      reason: decision.reason,
    },
    actions: [
      `优先执行：${OPTION_TEXT[decision.recommended].split(" — ")[0]}`,
      "启动本机网关后可获得 LLM 增强分析",
      "补充关键事实后再做一次验证",
    ],
  };
}

export function isNetworkFetchError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const msg = err.message.toLowerCase();
  return (
    msg.includes("failed to fetch") ||
    msg.includes("networkerror") ||
    msg.includes("network request failed") ||
    err.name === "AbortError"
  );
}
