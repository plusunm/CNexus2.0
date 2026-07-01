"""Backward-compatible view over Model Ontology."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .relationship_model_ontology import (
    MODEL_ONTOLOGY,
    build_card_from_library_model,
    instantiate_model_card,
    library_template_for_prompt,
    ontology_template_for_prompt,
    route_model,
    route_relationship_model,
)

RELATIONSHIP_LIBRARY_PHASE_ORDER = ("ambiguous_phase", "cold_phase", "breakdown_phase")


def _to_library_view(family_id: str) -> Dict[str, Any]:
    family = MODEL_ONTOLOGY[family_id]
    branches = (family.get("canonicalStructure") or {}).get("decisionModel", {}).get("fixedBranches") or {}
    tpl = family.get("template") or {}
    return {
        "id": family_id,
        "phaseOrder": family.get("phaseOrder"),
        "nextPhase": family.get("nextPhase"),
        "title": family.get("title"),
        "problemType": family.get("problemType"),
        "modelSummary": family.get("modelSummary"),
        "signalModel": tpl.get("signalModel"),
        "triggerConditions": tpl.get("triggerConditions"),
        "decisionLogic": "\n".join(str(branches.get(k) or "") for k in ("A", "B", "C", "D")),
        "decisionLogicByOption": branches,
        "riskModel": tpl.get("riskModel"),
        "actionTemplate": tpl.get("actionTemplate"),
        "reusabilityTags": tpl.get("reusabilityTags"),
    }


RELATIONSHIP_DECISION_LIBRARY: Dict[str, Dict[str, Any]] = {
    family_id: _to_library_view(family_id) for family_id in RELATIONSHIP_LIBRARY_PHASE_ORDER
}
