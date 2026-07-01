"""Compress RelationshipAnalysis → DecisionModelCard via Model Ontology Template System."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .relationship_model_ontology import (
    OntologyValidationError,
    constrain_llm_fill_to_ontology,
    instantiate_model_card,
    route_model,
    validate_card_ontology,
)


class ModelCardSchemaError(ValueError):
    pass


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _string_list(value: Any, *, limit: int = 6) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(row).strip() for row in value if str(row).strip()][:limit]


def rule_based_model_card(analysis: Dict[str, Any]) -> Dict[str, Any]:
    route = route_model(analysis)
    return instantiate_model_card(analysis, route)


def normalize_model_card_payload(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    title = _first(raw.get("title"))
    problem_type = _first(raw.get("problemType"), raw.get("problem_type"))
    model_summary = _first(raw.get("modelSummary"), raw.get("model_summary"))
    library_model_id = _first(raw.get("libraryModelId"), raw.get("library_model_id"))

    signal_in = raw.get("signalModel") if isinstance(raw.get("signalModel"), dict) else raw.get("signal_model")
    signal_in = signal_in if isinstance(signal_in, dict) else {}
    positive = _string_list(
        _first(signal_in.get("keyPositiveSignals"), signal_in.get("key_positive_signals")),
    )
    negative = _string_list(
        _first(signal_in.get("keyNegativeSignals"), signal_in.get("key_negative_signals")),
    )

    decision_in = raw.get("decisionModel") if isinstance(raw.get("decisionModel"), dict) else raw.get("decision_model")
    decision_in = decision_in if isinstance(decision_in, dict) else {}
    triggers = _string_list(
        _first(decision_in.get("triggerConditions"), decision_in.get("trigger_conditions")),
    )
    action_logic = _first(
        decision_in.get("recommendedActionLogic"),
        decision_in.get("recommended_action_logic"),
    )

    risk_in = raw.get("riskModel") if isinstance(raw.get("riskModel"), dict) else raw.get("risk_model")
    risk_in = risk_in if isinstance(risk_in, dict) else {}
    core_risks = _string_list(_first(risk_in.get("coreRisks"), risk_in.get("core_risks")))
    misjudgment = _string_list(
        _first(risk_in.get("misjudgmentSources"), risk_in.get("misjudgment_sources")),
    )

    action_template = _string_list(_first(raw.get("actionTemplate"), raw.get("action_template")))
    tags = _string_list(_first(raw.get("reusabilityTags"), raw.get("reusability_tags")))

    if not all([title, problem_type, model_summary, action_logic]):
        return None
    if not positive and not negative:
        return None
    if not triggers or not core_risks or not misjudgment or not action_template:
        return None

    payload: Dict[str, Any] = {
        "title": str(title).strip(),
        "problemType": str(problem_type).strip(),
        "modelSummary": str(model_summary).strip(),
        "signalModel": {
            "keyPositiveSignals": positive,
            "keyNegativeSignals": negative,
        },
        "decisionModel": {
            "triggerConditions": triggers,
            "recommendedActionLogic": str(action_logic).strip(),
        },
        "riskModel": {
            "coreRisks": core_risks,
            "misjudgmentSources": misjudgment,
        },
        "actionTemplate": action_template,
        "reusabilityTags": tags,
    }
    if library_model_id:
        payload["libraryModelId"] = str(library_model_id).strip()
    return payload


def validate_model_card(card: Dict[str, Any]) -> None:
    family_id = str(card.get("libraryModelId") or "generic")
    try:
        validate_card_ontology(card, family_id)
    except OntologyValidationError as exc:
        raise ModelCardSchemaError(str(exc)) from exc

    required_top = (
        "title", "problemType", "modelSummary", "signalModel",
        "decisionModel", "riskModel", "actionTemplate", "reusabilityTags",
    )
    for key in required_top:
        if key not in card:
            raise ModelCardSchemaError(f"missing card.{key}")


def merge_model_card(baseline: Dict[str, Any], llm_payload: Dict[str, Any]) -> Dict[str, Any]:
    family_id = str(baseline.get("libraryModelId") or "generic")
    try:
        return constrain_llm_fill_to_ontology(baseline, llm_payload if isinstance(llm_payload, dict) else {}, family_id)
    except OntologyValidationError:
        normalized = normalize_model_card_payload(llm_payload if isinstance(llm_payload, dict) else {})
        if not normalized:
            return baseline
        # Re-anchor to baseline structure — never accept LLM structure drift
        return baseline


def build_model_card(analysis: Dict[str, Any], llm_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    baseline = rule_based_model_card(analysis)
    if llm_payload:
        try:
            merged = merge_model_card(baseline, llm_payload)
            validate_model_card(merged)
            return merged
        except ModelCardSchemaError:
            pass
    validate_model_card(baseline)
    return baseline
