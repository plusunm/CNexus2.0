"""Model Ontology + Router + Card Template System (Python SSOT)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

ModelFamilyId = str  # ambiguous_phase | cold_phase | breakdown_phase | generic

ROMANCE_CANONICAL_STRUCTURE: Dict[str, Any] = {
    "signalModel": {
        "keyPositiveSignals": {"minItems": 0, "maxItems": 5},
        "keyNegativeSignals": {"minItems": 1, "maxItems": 5},
    },
    "decisionModel": {
        "triggerConditions": {"minItems": 3, "maxItems": 3},
        "fixedBranches": {},
    },
    "riskModel": {
        "coreRisks": {"minItems": 3, "maxItems": 3},
        "misjudgmentSources": {"minItems": 3, "maxItems": 3},
    },
    "actionTemplate": {"minItems": 4, "maxItems": 4},
    "reusabilityTags": {
        "minItems": 3,
        "maxItems": 5,
        "allowed": [
            "ambiguous_phase", "cold_phase", "breakdown_phase", "uncertainty",
            "attention_drop", "emotional_uncertainty", "undefined_relationship",
            "relationship_exit", "emotional_cutoff", "decision_required",
        ],
        "required": ["decision_required"],
    },
}


def _romance_family(
    family_id: str,
    meta: Dict[str, Any],
    threshold_rules: List[Dict[str, Any]],
    template: Dict[str, Any],
    branches: Dict[str, str],
) -> Dict[str, Any]:
    structure = {
        **ROMANCE_CANONICAL_STRUCTURE,
        "decisionModel": {
            **ROMANCE_CANONICAL_STRUCTURE["decisionModel"],
            "fixedBranches": branches,
        },
    }
    return {
        "id": family_id,
        **meta,
        "canonicalStructure": structure,
        "thresholdRules": threshold_rules,
        "template": template,
    }


MODEL_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "cold_phase": _romance_family(
        "cold_phase",
        {
            "title": "冷淡期判断模型",
            "problemType": "冷淡期识别",
            "modelSummary": "用于识别关系是否从正常互动进入结构性降温阶段",
            "phaseOrder": 1,
            "nextPhase": "breakdown_phase",
        },
        [
            {"id": "keyword_cold", "weight": 10, "description": "输入含冷淡/不理等关键词"},
            {"id": "stage_cold", "weight": 8, "description": "relationshipStage=cold"},
            {"id": "low_initiative", "weight": 4, "description": "initiativeLevel=low"},
            {"id": "low_interaction", "weight": 4, "description": "interactionFrequency=low"},
        ],
        {
            "signalModel": {
                "keyPositiveSignals": [
                    "仍保持基本回复", "偶尔主动发起对话", "情绪回应未完全消失", "仍存在日常信息交换",
                ],
                "keyNegativeSignals": [
                    "主动联系频率下降", "回复延迟显著增加", "对话长度缩短", "回避深度话题", "情绪反馈变弱",
                ],
            },
            "triggerConditions": ["主动性连续下降 ≥ 7天", "互动频率下降 ≥ 50%", "情绪回应强度下降"],
            "riskModel": {
                "coreRisks": ["将短期波动误判为关系衰退", "情绪焦虑导致过度解读", "单一信号（回复慢）过度权重"],
                "misjudgmentSources": ["单一信号过度解读", "情绪驱动判断", "时间窗口不足"],
            },
            "actionTemplate": ["发起一次「关系状态确认」", "观察7天互动变化", "暂停非必要主动联系", "记录对方响应模式"],
            "reusabilityTags": ["cold_phase", "uncertainty", "attention_drop", "decision_required"],
        },
        {
            "A": "如果（轻度冷淡 + 信息不完整）→ 观察期（不行动）",
            "B": "如果（持续冷淡 + 主动性下降）→ 主动沟通验证",
            "C": "如果（冷淡 + 回避沟通）→ 降低投入",
            "D": "如果（长期冷淡 + 无回应）→ 结束关系评估",
        },
    ),
    "ambiguous_phase": _romance_family(
        "ambiguous_phase",
        {
            "title": "暧昧期判断模型",
            "problemType": "关系推进",
            "modelSummary": "用于判断关系是否处于非明确关系但存在情绪吸引的阶段",
            "phaseOrder": 0,
            "nextPhase": "cold_phase",
        },
        [
            {"id": "keyword_ambiguous", "weight": 10, "description": "输入含暧昧/推进等关键词"},
            {"id": "uncertain_high_connection", "weight": 6, "description": "uncertain + 连接/互动未低"},
            {"id": "default_romance", "weight": 1, "description": "恋爱域默认起步"},
        ],
        {
            "signalModel": {
                "keyPositiveSignals": [
                    "高频互动但无明确关系定义", "情绪互动明显（调侃/试探）",
                    "主动性不对称但持续存在", "夜间或非正式时间沟通增加",
                ],
                "keyNegativeSignals": ["回应开始理性化", "对话减少情绪内容", "回避私人话题", "主动性下降"],
            },
            "triggerConditions": ["双方未定义关系但互动持续 ≥ 2周", "情绪互动占比 > 信息互动", "存在反复试探行为"],
            "riskModel": {
                "coreRisks": ["错误解读情绪互动为关系承诺", "单方投入过高", "长期停留在不定义状态"],
                "misjudgmentSources": ["情绪互动误判为承诺", "单方投入失衡", "回避定义导致拖延"],
            },
            "actionTemplate": ["轻度关系确认测试", "提出一次明确关系话题", "降低情绪投入测试反馈", "观察对方主动推进能力"],
            "reusabilityTags": ["ambiguous_phase", "emotional_uncertainty", "undefined_relationship", "decision_required"],
        },
        {
            "A": "如果（互动稳定但无推进）→ 设定边界观察",
            "B": "如果（高互动 + 未定义关系）→ 推进关系验证",
            "C": "如果（情绪下降 + 理性上升）→ 降级为普通关系",
            "D": "如果（单方高投入）→ 风险控制",
        },
    ),
    "breakdown_phase": _romance_family(
        "breakdown_phase",
        {
            "title": "分手期决策模型",
            "problemType": "是否继续关系",
            "modelSummary": "用于判断关系是否进入结构性不可逆衰退阶段",
            "phaseOrder": 2,
        },
        [
            {"id": "keyword_breakup", "weight": 10, "description": "输入含分手/结束等关键词"},
            {"id": "stage_broken", "weight": 8, "description": "relationshipStage=broken"},
        ],
        {
            "signalModel": {
                "keyPositiveSignals": [],
                "keyNegativeSignals": [
                    "长期回避沟通", "情绪连接消失", "主动性趋近于0", "冲突后无修复行为", "明确冷处理或忽视",
                ],
            },
            "triggerConditions": ["连续低互动 ≥ 14天", "情绪回应长期消失", "沟通尝试失败 ≥ 2次"],
            "riskModel": {
                "coreRisks": ["把暂时性冷静误判为结束", "情绪驱动快速决策", "没有验证直接退出"],
                "misjudgmentSources": ["暂时冷静误判为结束", "情绪驱动快速决策", "未验证即退出"],
            },
            "actionTemplate": ["停止主动投入", "进行最终沟通确认", "收集关系终止信号", "退出或降级关系结构"],
            "reusabilityTags": ["breakdown_phase", "relationship_exit", "emotional_cutoff", "decision_required"],
        },
        {
            "A": "如果（暂时冷静 + 仍有修复可能）→ 观察验证",
            "B": "如果（高冲突 + 无修复）→ 分手评估",
            "C": "如果（单向投入）→ 停止投入",
            "D": "如果（无回应 / 冷处理持续）→ 结束关系",
        },
    ),
    "generic": {
        "id": "generic",
        "title": "决策结构模型",
        "problemType": "决策分析",
        "modelSummary": "用于将局面信号、风险与行动压缩为可复用决策结构",
        "canonicalStructure": {
            "signalModel": {
                "keyPositiveSignals": {"minItems": 0, "maxItems": 4},
                "keyNegativeSignals": {"minItems": 0, "maxItems": 4},
            },
            "decisionModel": {
                "triggerConditions": {"minItems": 1, "maxItems": 3},
                "fixedBranches": {
                    "A": "如果触发条件成立 → 等待观察",
                    "B": "如果触发条件成立 → 主动验证",
                    "C": "如果触发条件成立 → 降低投入",
                    "D": "如果触发条件成立 → 明确决策",
                },
            },
            "riskModel": {
                "coreRisks": {"minItems": 1, "maxItems": 4},
                "misjudgmentSources": {"minItems": 1, "maxItems": 4},
            },
            "actionTemplate": {"minItems": 1, "maxItems": 4},
            "reusabilityTags": {
                "minItems": 1, "maxItems": 4,
                "allowed": ["decision_required", "generic_decision"],
                "required": ["decision_required"],
            },
        },
        "thresholdRules": [],
        "template": {
            "signalModel": {"keyPositiveSignals": [], "keyNegativeSignals": []},
            "triggerConditions": ["局面信号达到需决策阈值"],
            "riskModel": {"coreRisks": ["信息不对称", "情绪误判"], "misjudgmentSources": ["单一信号过度解读", "时间窗口不足"]},
            "actionTemplate": ["观察关键信号变化", "记录后续反馈", "避免不可逆决定"],
            "reusabilityTags": ["decision_required"],
        },
    },
}

ROMANCE_MODEL_FAMILY_IDS: Tuple[str, ...] = ("ambiguous_phase", "cold_phase", "breakdown_phase")

_NON_ROMANCE = re.compile(
    r"offer|跳槽|辞职|求职|裸辞|领导|老板|上级|甩锅|加薪|同事|朋友|借钱|催婚|父母|家庭|城市|回老家|人生|转行|读博",
    re.I,
)
_ROMANCE = re.compile(r"恋爱|喜欢|暧昧|分手|冷淡|不理|表白|对象|男友|女友|老公|老婆|相亲|在一起|推进|关系")


class OntologyValidationError(ValueError):
    pass


def _is_romance_input(text: str) -> bool:
    if _NON_ROMANCE.search(text):
        return False
    return bool(_ROMANCE.search(text))


def _rule_evaluators(analysis: Dict[str, Any]) -> Dict[str, bool]:
    meta = analysis.get("meta") or {}
    state = analysis.get("state") or {}
    text = str(meta.get("sourceInput") or "")
    stage = str(state.get("relationshipStage") or "")
    return {
        "keyword_cold": bool(re.search(r"冷淡|不理|冷处理|消失|不回|疏远", text)),
        "stage_cold": stage == "cold",
        "low_initiative": state.get("initiativeLevel") == "low",
        "low_interaction": state.get("interactionFrequency") == "low",
        "keyword_ambiguous": bool(re.search(r"暧昧|推进|表白|不明确|在一起吗", text)),
        "uncertain_high_connection": (
            stage == "uncertain"
            and state.get("emotionConnection") != "low"
            and state.get("interactionFrequency") != "low"
        ),
        "default_romance": True,
        "keyword_breakup": bool(re.search(r"分手|结束|离开|告别|离婚", text)),
        "stage_broken": stage == "broken",
    }


def route_model(analysis: Dict[str, Any]) -> Dict[str, Any]:
    text = str((analysis.get("meta") or {}).get("sourceInput") or "")

    if not _is_romance_input(text):
        return {
            "familyId": "generic",
            "family": MODEL_ONTOLOGY["generic"],
            "confidence": 1.0,
            "matchedRules": [],
            "reason": "非恋爱关系域 → generic 模型族",
            "isRomanceDomain": False,
        }

    if re.search(r"分手|结束|离开|告别|离婚", text):
        return {
            "familyId": "breakdown_phase",
            "family": MODEL_ONTOLOGY["breakdown_phase"],
            "confidence": 1.0,
            "matchedRules": ["keyword_breakup"],
            "reason": "显式关键词 → 分手期模型族",
            "isRomanceDomain": True,
        }
    if re.search(r"暧昧|推进|表白|不明确|在一起吗", text):
        return {
            "familyId": "ambiguous_phase",
            "family": MODEL_ONTOLOGY["ambiguous_phase"],
            "confidence": 1.0,
            "matchedRules": ["keyword_ambiguous"],
            "reason": "显式关键词 → 暧昧期模型族",
            "isRomanceDomain": True,
        }
    if re.search(r"冷淡|不理|冷处理|消失|不回|疏远", text):
        return {
            "familyId": "cold_phase",
            "family": MODEL_ONTOLOGY["cold_phase"],
            "confidence": 1.0,
            "matchedRules": ["keyword_cold"],
            "reason": "显式关键词 → 冷淡期模型族",
            "isRomanceDomain": True,
        }

    evals = _rule_evaluators(analysis)
    best_id = "ambiguous_phase"
    best_score = 0
    best_rules: List[str] = []

    for family_id in ROMANCE_MODEL_FAMILY_IDS:
        family = MODEL_ONTOLOGY[family_id]
        score = 0
        matched: List[str] = []
        for rule in family.get("thresholdRules") or []:
            if evals.get(rule["id"]):
                score += int(rule.get("weight") or 0)
                matched.append(rule["id"])
        if score > best_score:
            best_score = score
            best_id = family_id
            best_rules = matched

    family = MODEL_ONTOLOGY[best_id]
    max_possible = sum(int(r.get("weight") or 0) for r in family.get("thresholdRules") or []) or 1
    confidence = min(1.0, best_score / max_possible)
    descriptions = [
        str(r.get("description") or "")
        for r in family.get("thresholdRules") or []
        if r.get("id") in best_rules
    ]

    return {
        "familyId": best_id,
        "family": family,
        "confidence": confidence,
        "matchedRules": best_rules,
        "reason": "；".join(d for d in descriptions if d) or "恋爱域默认路由",
        "isRomanceDomain": True,
    }


def _merge_signal_slots(template: List[str], from_analysis: List[str], max_items: int) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for row in from_analysis + template:
        trimmed = re.sub(r"^当前", "", str(row)).strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        out.append(trimmed)
        if len(out) >= max_items:
            break
    return out


def _clamp_list(items: List[str], max_items: int) -> List[str]:
    cleaned = [str(r).strip() for r in items if str(r).strip()]
    return cleaned[:max_items]


def _generic_meta(text: str) -> Dict[str, str]:
    if re.search(r"offer|跳槽|辞职|求职|裸辞", text, re.I):
        return {"title": "职业机会评估模型", "problemType": "机会评估",
                "modelSummary": "用于在机会评估场景下，将信号、风险与行动压缩为可复用决策结构"}
    if re.search(r"领导|老板|上级|甩锅|加薪", text):
        return {"title": "职场上下级决策模型", "problemType": "权益与沟通",
                "modelSummary": "用于在权益与沟通场景下，将信号、风险与行动压缩为可复用决策结构"}
    if re.search(r"朋友|借钱|边界", text):
        return {"title": "人际边界决策模型", "problemType": "边界设定",
                "modelSummary": "用于在边界设定场景下，将信号、风险与行动压缩为可复用决策结构"}
    if re.search(r"催婚|父母|家庭", text):
        return {"title": "家庭压力决策模型", "problemType": "家庭压力",
                "modelSummary": "用于在家庭压力场景下，将信号、风险与行动压缩为可复用决策结构"}
    if re.search(r"城市|回老家|人生", text):
        return {"title": "人生方向选择模型", "problemType": "人生选择",
                "modelSummary": "用于在人生选择场景下，将信号、风险与行动压缩为可复用决策结构"}
    g = MODEL_ONTOLOGY["generic"]
    return {"title": g["title"], "problemType": g["problemType"], "modelSummary": g["modelSummary"]}


def instantiate_model_card(analysis: Dict[str, Any], route: Dict[str, Any]) -> Dict[str, Any]:
    family_id = str(route.get("familyId") or "generic")
    family = route.get("family") or MODEL_ONTOLOGY["generic"]
    structure = family.get("canonicalStructure") or {}
    tpl = family.get("template") or {}

    state = analysis.get("state") or {}
    signals = analysis.get("signals") or {}
    uncertainty = analysis.get("uncertainty") or {}
    decision = analysis.get("decision") or {}
    actions = analysis.get("actions") or []
    text = str((analysis.get("meta") or {}).get("sourceInput") or "")

    meta = _generic_meta(text) if family_id == "generic" else {
        "title": family["title"],
        "problemType": family["problemType"],
        "modelSummary": family["modelSummary"],
    }

    sig_schema = structure.get("signalModel") or {}
    pos_max = int((sig_schema.get("keyPositiveSignals") or {}).get("maxItems") or 5)
    neg_max = int((sig_schema.get("keyNegativeSignals") or {}).get("maxItems") or 5)
    sig_tpl = tpl.get("signalModel") or {}

    positive = _merge_signal_slots(
        list(sig_tpl.get("keyPositiveSignals") or []),
        [str(r) for r in (signals.get("positive") or [])],
        pos_max,
    )
    negative = _merge_signal_slots(
        list(sig_tpl.get("keyNegativeSignals") or []),
        [str(r) for r in (signals.get("negative") or [])],
        neg_max,
    )

    rec = str(decision.get("recommended") or "B")
    branches = (structure.get("decisionModel") or {}).get("fixedBranches") or {}
    action_logic = str(branches.get(rec) or "")

    risk_tpl = tpl.get("riskModel") or {}
    risk_schema = structure.get("riskModel") or {}
    core_max = int((risk_schema.get("coreRisks") or {}).get("maxItems") or 3)
    mis_max = int((risk_schema.get("misjudgmentSources") or {}).get("maxItems") or 3)

    core_risks = _clamp_list(
        [str(uncertainty.get("risk") or "")] + list(risk_tpl.get("coreRisks") or []),
        core_max,
    )
    missing = uncertainty.get("missingInfo") or []
    misjudgment = _clamp_list(
        [f"信息缺口：{row}" for row in missing[:1]] + list(risk_tpl.get("misjudgmentSources") or []),
        mis_max,
    )

    act_schema = structure.get("actionTemplate") or {}
    act_min = int(act_schema.get("minItems") or 1)
    act_max = int(act_schema.get("maxItems") or 4)
    action_template = [str(r).strip() for r in actions if str(r).strip()][:act_max]
    if len(action_template) < act_min:
        action_template = list(tpl.get("actionTemplate") or [])[:act_max]

    card = {
        **meta,
        "libraryModelId": None if family_id == "generic" else family_id,
        "signalModel": {"keyPositiveSignals": positive, "keyNegativeSignals": negative},
        "decisionModel": {
            "triggerConditions": list(tpl.get("triggerConditions") or []),
            "recommendedActionLogic": action_logic,
        },
        "riskModel": {"coreRisks": core_risks, "misjudgmentSources": misjudgment},
        "actionTemplate": action_template,
        "reusabilityTags": list(tpl.get("reusabilityTags") or []),
    }
    validate_card_ontology(card, family_id)
    return card


def validate_card_ontology(card: Dict[str, Any], family_id: str) -> None:
    family = MODEL_ONTOLOGY.get(family_id) or MODEL_ONTOLOGY["generic"]
    tpl = family.get("template") or {}

    if family_id != "generic" and card.get("libraryModelId") != family_id:
        raise OntologyValidationError(f"libraryModelId must be {family_id}")

    if family_id != "generic" and card.get("title") != family.get("title"):
        raise OntologyValidationError("title drift from ontology")

    triggers = (card.get("decisionModel") or {}).get("triggerConditions") or []
    if family_id != "generic" and len(triggers) != len(tpl.get("triggerConditions") or []):
        raise OntologyValidationError("triggerConditions must match ontology template count")


def constrain_llm_fill_to_ontology(
    baseline: Dict[str, Any],
    llm_payload: Dict[str, Any],
    family_id: str,
) -> Dict[str, Any]:
    family = MODEL_ONTOLOGY.get(family_id) or MODEL_ONTOLOGY["generic"]
    structure = family.get("canonicalStructure") or {}
    tpl = family.get("template") or {}
    sig_schema = structure.get("signalModel") or {}

    signal_in = llm_payload.get("signalModel") if isinstance(llm_payload.get("signalModel"), dict) else llm_payload.get("signal_model")
    signal_in = signal_in if isinstance(signal_in, dict) else {}

    positive = (baseline.get("signalModel") or {}).get("keyPositiveSignals") or []
    negative = (baseline.get("signalModel") or {}).get("keyNegativeSignals") or []

    llm_pos = signal_in.get("keyPositiveSignals") or signal_in.get("key_positive_signals")
    llm_neg = signal_in.get("keyNegativeSignals") or signal_in.get("key_negative_signals")
    sig_tpl = tpl.get("signalModel") or {}

    if isinstance(llm_pos, list) and llm_pos:
        positive = _merge_signal_slots(
            list(sig_tpl.get("keyPositiveSignals") or []),
            [str(r) for r in llm_pos],
            int((sig_schema.get("keyPositiveSignals") or {}).get("maxItems") or 5),
        )
    if isinstance(llm_neg, list) and llm_neg:
        negative = _merge_signal_slots(
            list(sig_tpl.get("keyNegativeSignals") or []),
            [str(r) for r in llm_neg],
            int((sig_schema.get("keyNegativeSignals") or {}).get("maxItems") or 5),
        )

    actions = baseline.get("actionTemplate") or []
    llm_actions = llm_payload.get("actionTemplate") or llm_payload.get("action_template")
    act_schema = structure.get("actionTemplate") or {}
    act_min = int(act_schema.get("minItems") or 1)
    act_max = int(act_schema.get("maxItems") or 4)
    if isinstance(llm_actions, list) and len(llm_actions) >= act_min:
        actions = _clamp_list([str(r) for r in llm_actions], act_max)

    merged = {
        **baseline,
        "signalModel": {"keyPositiveSignals": positive, "keyNegativeSignals": negative},
        "actionTemplate": actions,
    }
    validate_card_ontology(merged, family_id)
    return merged


def ontology_template_for_prompt(family_id: str) -> Dict[str, Any]:
    family = MODEL_ONTOLOGY.get(family_id) or MODEL_ONTOLOGY["generic"]
    branches = (family.get("canonicalStructure") or {}).get("decisionModel", {}).get("fixedBranches") or {}
    decision_logic = "\n".join(str(branches.get(k) or "") for k in ("A", "B", "C", "D"))
    return {
        "family_id": family_id,
        "title": family.get("title"),
        "problem_type": family.get("problemType"),
        "model_summary": family.get("modelSummary"),
        "canonical_structure": family.get("canonicalStructure"),
        "template": family.get("template"),
        "decision_logic": decision_logic,
        "fill_policy": "只能填充 signal_model 与 action_template 的槽位文本，不得改变结构、标签、触发条件、决策分支",
    }


# Backward-compatible aliases
route_relationship_model = route_model
build_card_from_library_model = instantiate_model_card


def library_template_for_prompt(model_id: str) -> Optional[Dict[str, Any]]:
    if model_id in MODEL_ONTOLOGY:
        return ontology_template_for_prompt(model_id)
    return None
