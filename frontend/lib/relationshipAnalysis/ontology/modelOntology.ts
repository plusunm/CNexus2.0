/**
 * Model Ontology — CNexus cognitive model families (structure SSOT).
 * All cards of the same family MUST share identical structural skeleton.
 */

import type { DecisionOptionId } from "../types/relationship";

export type ModelFamilyId = "ambiguous_phase" | "cold_phase" | "breakdown_phase" | "generic";

export type FieldListSchema = {
  minItems: number;
  maxItems: number;
};

export type CanonicalStructureSchema = {
  signalModel: {
    keyPositiveSignals: FieldListSchema;
    keyNegativeSignals: FieldListSchema;
  };
  decisionModel: {
    triggerConditions: FieldListSchema;
    /** Branches are fixed per family — LLM cannot invent new ones */
    fixedBranches: Record<DecisionOptionId, string>;
  };
  riskModel: {
    coreRisks: FieldListSchema;
    misjudgmentSources: FieldListSchema;
  };
  actionTemplate: FieldListSchema;
  reusabilityTags: FieldListSchema & { allowed: readonly string[]; required: readonly string[] };
};

export type ThresholdRule = {
  id: string;
  weight: number;
  description: string;
};

export type ModelFamilyTemplate = {
  signalModel: { keyPositiveSignals: string[]; keyNegativeSignals: string[] };
  triggerConditions: string[];
  riskModel: { coreRisks: string[]; misjudgmentSources: string[] };
  actionTemplate: string[];
  reusabilityTags: string[];
};

export type ModelFamily = {
  id: ModelFamilyId;
  title: string;
  problemType: string;
  modelSummary: string;
  phaseOrder?: 0 | 1 | 2;
  nextPhase?: ModelFamilyId;
  canonicalStructure: CanonicalStructureSchema;
  /** Router scoring rules — evaluated against CanonicalSchema */
  thresholdRules: ThresholdRule[];
  template: ModelFamilyTemplate;
};

/** Shared romance-family structure — all three phases use identical shape */
export const ROMANCE_CANONICAL_STRUCTURE: CanonicalStructureSchema = {
  signalModel: {
    keyPositiveSignals: { minItems: 0, maxItems: 5 },
    keyNegativeSignals: { minItems: 1, maxItems: 5 },
  },
  decisionModel: {
    triggerConditions: { minItems: 3, maxItems: 3 },
    fixedBranches: { A: "", B: "", C: "", D: "" }, // filled per family
  },
  riskModel: {
    coreRisks: { minItems: 3, maxItems: 3 },
    misjudgmentSources: { minItems: 3, maxItems: 3 },
  },
  actionTemplate: { minItems: 4, maxItems: 4 },
  reusabilityTags: {
    minItems: 3,
    maxItems: 5,
    allowed: [
      "ambiguous_phase",
      "cold_phase",
      "breakdown_phase",
      "uncertainty",
      "attention_drop",
      "emotional_uncertainty",
      "undefined_relationship",
      "relationship_exit",
      "emotional_cutoff",
      "decision_required",
    ],
    required: ["decision_required"],
  },
};

function romanceFamily(
  id: Exclude<ModelFamilyId, "generic">,
  meta: Pick<ModelFamily, "title" | "problemType" | "modelSummary" | "phaseOrder" | "nextPhase">,
  thresholdRules: ThresholdRule[],
  template: ModelFamilyTemplate,
  branches: Record<DecisionOptionId, string>,
): ModelFamily {
  return {
    id,
    ...meta,
    canonicalStructure: {
      ...ROMANCE_CANONICAL_STRUCTURE,
      decisionModel: {
        ...ROMANCE_CANONICAL_STRUCTURE.decisionModel,
        fixedBranches: branches,
      },
      reusabilityTags: {
        ...ROMANCE_CANONICAL_STRUCTURE.reusabilityTags,
        required: [...template.reusabilityTags.filter((t) => t !== "decision_required"), "decision_required"],
      },
    },
    thresholdRules,
    template,
  };
}

export const MODEL_ONTOLOGY: Record<ModelFamilyId, ModelFamily> = {
  cold_phase: romanceFamily(
    "cold_phase",
    {
      title: "冷淡期判断模型",
      problemType: "冷淡期识别",
      modelSummary: "用于识别关系是否从正常互动进入结构性降温阶段",
      phaseOrder: 1,
      nextPhase: "breakdown_phase",
    },
    [
      { id: "keyword_cold", weight: 10, description: "输入含冷淡/不理等关键词" },
      { id: "stage_cold", weight: 8, description: "relationshipStage=cold" },
      { id: "low_initiative", weight: 4, description: "initiativeLevel=low" },
      { id: "low_interaction", weight: 4, description: "interactionFrequency=low" },
    ],
    {
      signalModel: {
        keyPositiveSignals: [
          "仍保持基本回复",
          "偶尔主动发起对话",
          "情绪回应未完全消失",
          "仍存在日常信息交换",
        ],
        keyNegativeSignals: [
          "主动联系频率下降",
          "回复延迟显著增加",
          "对话长度缩短",
          "回避深度话题",
          "情绪反馈变弱",
        ],
      },
      triggerConditions: [
        "主动性连续下降 ≥ 7天",
        "互动频率下降 ≥ 50%",
        "情绪回应强度下降",
      ],
      riskModel: {
        coreRisks: [
          "将短期波动误判为关系衰退",
          "情绪焦虑导致过度解读",
          "单一信号（回复慢）过度权重",
        ],
        misjudgmentSources: ["单一信号过度解读", "情绪驱动判断", "时间窗口不足"],
      },
      actionTemplate: [
        "发起一次「关系状态确认」",
        "观察7天互动变化",
        "暂停非必要主动联系",
        "记录对方响应模式",
      ],
      reusabilityTags: ["cold_phase", "uncertainty", "attention_drop", "decision_required"],
    },
    {
      A: "如果（轻度冷淡 + 信息不完整）→ 观察期（不行动）",
      B: "如果（持续冷淡 + 主动性下降）→ 主动沟通验证",
      C: "如果（冷淡 + 回避沟通）→ 降低投入",
      D: "如果（长期冷淡 + 无回应）→ 结束关系评估",
    },
  ),

  ambiguous_phase: romanceFamily(
    "ambiguous_phase",
    {
      title: "暧昧期判断模型",
      problemType: "关系推进",
      modelSummary: "用于判断关系是否处于非明确关系但存在情绪吸引的阶段",
      phaseOrder: 0,
      nextPhase: "cold_phase",
    },
    [
      { id: "keyword_ambiguous", weight: 10, description: "输入含暧昧/推进等关键词" },
      { id: "uncertain_high_connection", weight: 6, description: "uncertain + 连接/互动未低" },
      { id: "default_romance", weight: 1, description: "恋爱域默认起步" },
    ],
    {
      signalModel: {
        keyPositiveSignals: [
          "高频互动但无明确关系定义",
          "情绪互动明显（调侃/试探）",
          "主动性不对称但持续存在",
          "夜间或非正式时间沟通增加",
        ],
        keyNegativeSignals: [
          "回应开始理性化",
          "对话减少情绪内容",
          "回避私人话题",
          "主动性下降",
        ],
      },
      triggerConditions: [
        "双方未定义关系但互动持续 ≥ 2周",
        "情绪互动占比 > 信息互动",
        "存在反复试探行为",
      ],
      riskModel: {
        coreRisks: [
          "错误解读情绪互动为关系承诺",
          "单方投入过高",
          "长期停留在不定义状态",
        ],
        misjudgmentSources: ["情绪互动误判为承诺", "单方投入失衡", "回避定义导致拖延"],
      },
      actionTemplate: [
        "轻度关系确认测试",
        "提出一次明确关系话题",
        "降低情绪投入测试反馈",
        "观察对方主动推进能力",
      ],
      reusabilityTags: [
        "ambiguous_phase",
        "emotional_uncertainty",
        "undefined_relationship",
        "decision_required",
      ],
    },
    {
      A: "如果（互动稳定但无推进）→ 设定边界观察",
      B: "如果（高互动 + 未定义关系）→ 推进关系验证",
      C: "如果（情绪下降 + 理性上升）→ 降级为普通关系",
      D: "如果（单方高投入）→ 风险控制",
    },
  ),

  breakdown_phase: romanceFamily(
    "breakdown_phase",
    {
      title: "分手期决策模型",
      problemType: "是否继续关系",
      modelSummary: "用于判断关系是否进入结构性不可逆衰退阶段",
      phaseOrder: 2,
    },
    [
      { id: "keyword_breakup", weight: 10, description: "输入含分手/结束等关键词" },
      { id: "stage_broken", weight: 8, description: "relationshipStage=broken" },
    ],
    {
      signalModel: {
        keyPositiveSignals: [],
        keyNegativeSignals: [
          "长期回避沟通",
          "情绪连接消失",
          "主动性趋近于0",
          "冲突后无修复行为",
          "明确冷处理或忽视",
        ],
      },
      triggerConditions: [
        "连续低互动 ≥ 14天",
        "情绪回应长期消失",
        "沟通尝试失败 ≥ 2次",
      ],
      riskModel: {
        coreRisks: ["把暂时性冷静误判为结束", "情绪驱动快速决策", "没有验证直接退出"],
        misjudgmentSources: ["暂时冷静误判为结束", "情绪驱动快速决策", "未验证即退出"],
      },
      actionTemplate: [
        "停止主动投入",
        "进行最终沟通确认",
        "收集关系终止信号",
        "退出或降级关系结构",
      ],
      reusabilityTags: ["breakdown_phase", "relationship_exit", "emotional_cutoff", "decision_required"],
    },
    {
      A: "如果（暂时冷静 + 仍有修复可能）→ 观察验证",
      B: "如果（高冲突 + 无修复）→ 分手评估",
      C: "如果（单向投入）→ 停止投入",
      D: "如果（无回应 / 冷处理持续）→ 结束关系",
    },
  ),

  generic: {
    id: "generic",
    title: "决策结构模型",
    problemType: "决策分析",
    modelSummary: "用于将局面信号、风险与行动压缩为可复用决策结构",
    canonicalStructure: {
      signalModel: {
        keyPositiveSignals: { minItems: 0, maxItems: 4 },
        keyNegativeSignals: { minItems: 0, maxItems: 4 },
      },
      decisionModel: {
        triggerConditions: { minItems: 1, maxItems: 3 },
        fixedBranches: {
          A: "如果触发条件成立 → 等待观察",
          B: "如果触发条件成立 → 主动验证",
          C: "如果触发条件成立 → 降低投入",
          D: "如果触发条件成立 → 明确决策",
        },
      },
      riskModel: {
        coreRisks: { minItems: 1, maxItems: 4 },
        misjudgmentSources: { minItems: 1, maxItems: 4 },
      },
      actionTemplate: { minItems: 1, maxItems: 4 },
      reusabilityTags: {
        minItems: 1,
        maxItems: 4,
        allowed: ["decision_required", "generic_decision"],
        required: ["decision_required"],
      },
    },
    thresholdRules: [],
    template: {
      signalModel: { keyPositiveSignals: [], keyNegativeSignals: [] },
      triggerConditions: ["局面信号达到需决策阈值"],
      riskModel: {
        coreRisks: ["信息不对称", "情绪误判"],
        misjudgmentSources: ["单一信号过度解读", "时间窗口不足"],
      },
      actionTemplate: ["观察关键信号变化", "记录后续反馈", "避免不可逆决定"],
      reusabilityTags: ["decision_required"],
    },
  },
};

export const ROMANCE_MODEL_FAMILY_IDS: ModelFamilyId[] = [
  "ambiguous_phase",
  "cold_phase",
  "breakdown_phase",
];

export function getModelFamily(id: ModelFamilyId): ModelFamily {
  return MODEL_ONTOLOGY[id];
}

export function familyDecisionLogic(family: ModelFamily): string {
  const branches = family.canonicalStructure.decisionModel.fixedBranches;
  return (["A", "B", "C", "D"] as DecisionOptionId[])
    .map((k) => branches[k])
    .join("\n");
}
