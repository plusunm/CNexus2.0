"""Canonical RelationshipAnalysis — validate, rule fallback, card envelope."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1.0"
LEVEL_BANDS = frozenset({"high", "medium", "low"})
STAGES = frozenset({"stable", "cold", "uncertain", "broken"})
DECISION_IDS = ("A", "B", "C", "D")

DECISION_OPTION_TEXT = {
    "A": "等待观察 — 暂不行动，收集更多互动信号后再判断",
    "B": "主动沟通验证 — 用低压力方式确认对方状态与意图",
    "C": "降低投入 — 减少情绪消耗，保留边界与自我价值",
    "D": "明确决策 — 在信息足够时做出继续或结束的清晰选择",
}

RISK_BY_STAGE = {
    "stable": "整体风险偏低，但仍需避免过度解读单次互动",
    "cold": "冷淡信号持续可能放大误解，宜尽快验证而非猜测",
    "uncertain": "信息不足时贸然行动容易误判，优先补齐关键事实",
    "broken": "信任与情绪双低，继续拖延可能增加情绪消耗",
}


class CanonicalSchemaError(ValueError):
    pass


def _emotion_valence(raw: Optional[Dict[str, Any]]) -> float:
    if not raw:
        return 0.0
    if raw.get("valence") is not None:
        return float(raw["valence"])
    if raw.get("val") is not None:
        return float(raw["val"])
    return 0.0


def _relationship_trust(converse: Dict[str, Any], status: Optional[Dict[str, Any]]) -> float:
    rel = converse.get("relationship") or (status or {}).get("relationship") or {}
    if isinstance(rel.get("trust"), (int, float)):
        return float(rel["trust"])
    if isinstance(rel.get("closeness"), (int, float)):
        return float(rel["closeness"])
    if isinstance(rel.get("tone"), (int, float)):
        return (float(rel["tone"]) + 1.0) / 2.0
    return 0.5


def _level_from_score(score: float, invert: bool = False) -> str:
    v = 1.0 - score if invert else score
    if v < 0.35:
        return "low"
    if v > 0.65:
        return "high"
    return "medium"


def rule_based_analysis(
    source_input: str,
    converse: Dict[str, Any],
    status: Optional[Dict[str, Any]] = None,
    *,
    analysis_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Map unstable backend JSON → canonical RelationshipAnalysis (no LLM)."""
    import datetime

    text = (source_input or "").strip()
    emotion = converse.get("emotion") or (status or {}).get("emotion") or {}
    valence = _emotion_valence(emotion if isinstance(emotion, dict) else {})
    arousal = float(emotion.get("arousal", 0.5) if isinstance(emotion, dict) else 0.5)
    trust = _relationship_trust(converse, status)
    cog = converse.get("cog_state") if isinstance(converse.get("cog_state"), dict) else {}
    recall = float(cog.get("recall_strength", 0.5))
    hits = int(converse.get("activation_injected") or len(converse.get("activation_hits") or []))

    emotion_connection = "low" if valence < -0.25 else "high" if valence > 0.25 else "medium"
    initiative_level = (
        "low" if arousal < 0.35 or recall < 0.4 else "high" if recall > 0.65 or arousal > 0.65 else "medium"
    )
    interaction_frequency = "low" if hits == 0 else "high" if hits >= 3 else "medium"

    if trust < 0.35 and valence < -0.2:
        relationship_stage = "broken"
    elif valence < -0.2 or interaction_frequency == "low":
        relationship_stage = "cold"
    elif trust >= 0.55 and emotion_connection != "low":
        relationship_stage = "stable"
    else:
        relationship_stage = "uncertain"

    positive: List[str] = []
    negative: List[str] = []
    for hit in converse.get("activation_hits") or []:
        if not isinstance(hit, dict):
            continue
        title = str(hit.get("title") or "").strip()
        if not title:
            continue
        score = float(hit.get("score") or 0)
        (positive if score >= 0.45 else negative).append(title)

    if valence > 0.2:
        positive.append("当前情绪基调偏正向")
    elif valence < -0.2:
        negative.append("当前情绪基调偏负向")

    intent = str(converse.get("intent") or cog.get("active_intent") or "").lower()
    if "recall" in intent or "memory" in intent:
        positive.append("系统召回了相关历史记忆")
    if not positive:
        positive.append("问题已纳入结构化分析框架")
    if not negative and re.search(r"不理|冷淡|分手|消失|不回", text):
        negative.append("输入描述暗示互动减少或回应延迟")
    if not negative and re.search(r"甩锅|抢功|压榨|PUA|领导|老板|上级", text):
        negative.append("输入描述暗示职场关系存在压力或不公平")
    if not negative and re.search(r"跳槽|offer|裸辞|求职|面试|辞职", text):
        negative.append("输入描述暗示职业选择存在机会与风险并存")

    missing_info: List[str] = []
    ctx = str(converse.get("activation_context") or "").strip()
    if hits == 0:
        missing_info.append("缺少可召回的相关历史记忆")
    if not ctx:
        missing_info.append("缺少关键事实或对方/对方立场描述")
    if not converse.get("relationship") and not converse.get("emotion"):
        missing_info.append("局面快照信息不完整")
    if not missing_info:
        missing_info.append("部分推断基于有限上下文，需后续验证")

    recommended = "A"
    reason = "信号尚不充分，先观察再行动风险更低"
    if re.search(r"分手|结束|离开|裸辞|立刻辞职", text) and (trust < 0.4 or re.search(r"裸辞|立刻辞职", text)):
        recommended, reason = "D", "问题指向重大去留，适合先做明确决策而非拖延"
    elif re.search(r"跳槽|offer|加薪|老板|领导|上级|甩锅", text):
        recommended, reason = "B", "职场/求职类问题宜先沟通或核实关键信息再行动"
    elif hits == 0 or trust < 0.45:
        recommended, reason = "B", "信息不足，优先通过沟通或调研验证假设"
    elif valence < -0.3:
        recommended, reason = "C", "局面偏冷或投入偏高，建议先降低消耗、保护边界"
    elif re.search(r"暧昧|推进|表白", text):
        recommended, reason = "B", "关系推进类问题适合小步验证，避免过度解读"

    options = dict(DECISION_OPTION_TEXT)
    primary = options[recommended]
    actions = [
        f"优先执行：{primary}",
        "记录后续 1–2 次关键反馈，用于更新判断",
        "若不确定性项未消除，避免做不可逆决定",
    ]

    analysis = {
        "meta": {
            "id": analysis_id or f"ra-{int(datetime.datetime.now().timestamp() * 1000)}",
            "sourceInput": text,
            "createdAt": created_at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "schemaVersion": SCHEMA_VERSION,
        },
        "state": {
            "emotionConnection": emotion_connection,
            "initiativeLevel": initiative_level,
            "interactionFrequency": interaction_frequency,
            "relationshipStage": relationship_stage,
        },
        "signals": {"positive": positive[:6], "negative": negative[:6]},
        "uncertainty": {
            "missingInfo": missing_info[:4],
            "risk": RISK_BY_STAGE[relationship_stage],
        },
        "decision": {"options": options, "recommended": recommended, "reason": reason},
        "actions": actions,
    }
    validate_analysis(analysis)
    return analysis


def validate_analysis(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalSchemaError("analysis must be object")

    meta = value.get("meta")
    if not isinstance(meta, dict):
        raise CanonicalSchemaError("meta invalid")
    if meta.get("schemaVersion") != SCHEMA_VERSION:
        raise CanonicalSchemaError("schemaVersion mismatch")

    state = value.get("state")
    if not isinstance(state, dict):
        raise CanonicalSchemaError("state invalid")
    for key in ("emotionConnection", "initiativeLevel", "interactionFrequency"):
        if state.get(key) not in LEVEL_BANDS:
            raise CanonicalSchemaError(f"state.{key} invalid")
    if state.get("relationshipStage") not in STAGES:
        raise CanonicalSchemaError("state.relationshipStage invalid")

    signals = value.get("signals")
    if not isinstance(signals, dict):
        raise CanonicalSchemaError("signals invalid")
    for key in ("positive", "negative"):
        if not isinstance(signals.get(key), list):
            raise CanonicalSchemaError(f"signals.{key} invalid")

    uncertainty = value.get("uncertainty")
    if not isinstance(uncertainty, dict):
        raise CanonicalSchemaError("uncertainty invalid")
    if not isinstance(uncertainty.get("missingInfo"), list):
        raise CanonicalSchemaError("uncertainty.missingInfo invalid")
    if not str(uncertainty.get("risk") or "").strip():
        raise CanonicalSchemaError("uncertainty.risk invalid")

    decision = value.get("decision")
    if not isinstance(decision, dict):
        raise CanonicalSchemaError("decision invalid")
    options = decision.get("options")
    if not isinstance(options, dict):
        raise CanonicalSchemaError("decision.options invalid")
    for opt_id in DECISION_IDS:
        if not str(options.get(opt_id) or "").strip():
            raise CanonicalSchemaError(f"decision.options.{opt_id} invalid")
    if decision.get("recommended") not in DECISION_IDS:
        raise CanonicalSchemaError("decision.recommended invalid")
    if not str(decision.get("reason") or "").strip():
        raise CanonicalSchemaError("decision.reason invalid")

    actions = value.get("actions")
    if not isinstance(actions, list) or not actions or not all(isinstance(a, str) and a for a in actions):
        raise CanonicalSchemaError("actions invalid")

    return value


def _normalize_level(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip().lower()
    if raw in LEVEL_BANDS:
        return raw
    aliases = {"高": "high", "中": "medium", "低": "low", "h": "high", "m": "medium", "l": "low"}
    return aliases.get(raw)


def _normalize_stage(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip().lower()
    stage_aliases = {
        "breaking": "broken",
        "break": "broken",
        "破裂": "broken",
        "破裂风险": "broken",
        "stable": "stable",
        "稳定": "stable",
        "cold": "cold",
        "冷淡": "cold",
        "uncertain": "uncertain",
        "不确定": "uncertain",
        "broken": "broken",
    }
    mapped = stage_aliases.get(raw, raw)
    return mapped if mapped in STAGES else None


def _normalize_decision_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip().upper()
    return raw if raw in DECISION_IDS else None


def _first(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        return value
    return None


def normalize_llm_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Anti-pollution: map LLM snake_case / flat decision → canonical fill shape."""
    if not isinstance(raw, dict):
        raise CanonicalSchemaError("llm payload must be object")

    state_in = raw.get("state") if isinstance(raw.get("state"), dict) else {}
    state = {}
    ec = _normalize_level(_first(state_in.get("emotionConnection"), state_in.get("emotion_connection")))
    il = _normalize_level(_first(state_in.get("initiativeLevel"), state_in.get("initiative_level")))
    iff = _normalize_level(_first(state_in.get("interactionFrequency"), state_in.get("interaction_frequency")))
    rs = _normalize_stage(_first(state_in.get("relationshipStage"), state_in.get("relationship_stage")))
    if ec:
        state["emotionConnection"] = ec
    if il:
        state["initiativeLevel"] = il
    if iff:
        state["interactionFrequency"] = iff
    if rs:
        state["relationshipStage"] = rs

    signals_in = raw.get("signals") if isinstance(raw.get("signals"), dict) else {}
    signals: Dict[str, List[str]] = {}
    for key in ("positive", "negative"):
        rows = signals_in.get(key)
        if isinstance(rows, list):
            cleaned = [str(row).strip() for row in rows if str(row).strip()]
            if cleaned:
                signals[key] = cleaned[:8]

    uncertainty_in = raw.get("uncertainty") if isinstance(raw.get("uncertainty"), dict) else {}
    uncertainty: Dict[str, Any] = {}
    missing = _first(uncertainty_in.get("missingInfo"), uncertainty_in.get("missing_info"))
    if isinstance(missing, list):
        cleaned = [str(row).strip() for row in missing if str(row).strip()]
        if cleaned:
            uncertainty["missingInfo"] = cleaned[:6]
    risk = _first(uncertainty_in.get("risk"), uncertainty_in.get("risk_of_misjudgment"))
    if isinstance(risk, str) and risk.strip():
        uncertainty["risk"] = risk.strip()

    decision_in = raw.get("decision") if isinstance(raw.get("decision"), dict) else {}
    decision: Dict[str, Any] = {}
    options_in = decision_in.get("options") if isinstance(decision_in.get("options"), dict) else {}
    options: Dict[str, str] = {}
    for opt_id in DECISION_IDS:
        text = _first(options_in.get(opt_id), decision_in.get(opt_id))
        if isinstance(text, str) and text.strip():
            options[opt_id] = text.strip()
    if options:
        decision["options"] = options
    recommended = _normalize_decision_id(decision_in.get("recommended"))
    if recommended:
        decision["recommended"] = recommended
    reason = decision_in.get("reason")
    if isinstance(reason, str) and reason.strip():
        decision["reason"] = reason.strip()

    actions_in = raw.get("actions")
    actions: List[str] = []
    if isinstance(actions_in, list):
        actions = [str(row).strip() for row in actions_in if str(row).strip()][:6]

    payload: Dict[str, Any] = {}
    if state:
        payload["state"] = state
    if signals:
        payload["signals"] = signals
    if uncertainty:
        payload["uncertainty"] = uncertainty
    if decision:
        payload["decision"] = decision
    if actions:
        payload["actions"] = actions
    return payload


def merge_llm_fill(base: Dict[str, Any], llm_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Overlay normalized LLM fill onto rule baseline; re-validate."""
    normalized = normalize_llm_payload(llm_payload if isinstance(llm_payload, dict) else {})
    merged = {
        "meta": dict(base.get("meta") or {}),
        "state": {**(base.get("state") or {}), **(normalized.get("state") or {})},
        "signals": {**(base.get("signals") or {}), **(normalized.get("signals") or {})},
        "uncertainty": {**(base.get("uncertainty") or {}), **(normalized.get("uncertainty") or {})},
        "decision": {**(base.get("decision") or {}), **(normalized.get("decision") or {})},
        "actions": normalized.get("actions") or base.get("actions"),
    }
    base_options = (base.get("decision") or {}).get("options") or {}
    llm_options = ((normalized.get("decision") or {}).get("options") or {})
    merged_options = dict(base_options)
    for opt_id in DECISION_IDS:
        if str(llm_options.get(opt_id) or "").strip():
            merged_options[opt_id] = str(llm_options[opt_id]).strip()
    merged["decision"]["options"] = merged_options
    if normalized.get("decision", {}).get("recommended"):
        merged["decision"]["recommended"] = normalized["decision"]["recommended"]
    if normalized.get("decision", {}).get("reason"):
        merged["decision"]["reason"] = normalized["decision"]["reason"]
    validate_analysis(merged)
    return merged


def to_card_envelope(
    analysis: Dict[str, Any],
    model_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from .relationship_card_model import build_model_card

    validate_analysis(analysis)
    model = build_model_card(analysis, model_payload)
    return {**analysis, "card": model}


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    import json

    raw = (text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None
