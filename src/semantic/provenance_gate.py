"""Provenance gate — truth enforcement for composed SCP slots (L3)."""

from __future__ import annotations

from typing import Dict

from .dimensions import (
    DIMENSION_DECISION,
    DIMENSION_FACT,
    DIMENSION_PERSONA_SUMMARY,
    DIMENSION_PROCEDURE,
    DIMENSION_STYLE,
)
from .types import ArbitrationDecision, SCPRequest, SemanticCandidate, TurnProfile

PROVENANCE_PERSONA_SYNTHETIC = "persona-synthetic"
PROVENANCE_POLICY_LAYER = "policy-layer"


def provenance_for_dimension(dimension: str, *, thinking_mode: str = "precision") -> str:
    dim = str(dimension or "").strip().lower()
    if dim in (DIMENSION_STYLE, DIMENSION_PERSONA_SUMMARY):
        return PROVENANCE_PERSONA_SYNTHETIC
    if dim == DIMENSION_PROCEDURE:
        return PROVENANCE_POLICY_LAYER
    if dim == DIMENSION_DECISION:
        return "audit-preview"
    _ = thinking_mode
    return "local-full"


def is_authoritative(provenance: str) -> bool:
    return provenance not in (PROVENANCE_PERSONA_SYNTHETIC, PROVENANCE_POLICY_LAYER)


def is_synthetic_provenance(provenance: str) -> bool:
    return provenance in (PROVENANCE_PERSONA_SYNTHETIC, PROVENANCE_POLICY_LAYER)


class ProvenanceGate:
    """Format SCP slots with honesty wrappers — never promote synthetic to fact."""

    def format_candidate(self, candidate: SemanticCandidate, *, profile: TurnProfile) -> str:
        content = str(candidate.content or "").strip()
        if not content:
            return ""
        provenance = provenance_for_dimension(candidate.dimension, thinking_mode=profile.thinking_mode)
        if provenance == PROVENANCE_PERSONA_SYNTHETIC:
            return (
                f"[Style-Guide, not fact · {provenance}]\n"
                f"{content}\n"
                f"[End style guide — do not cite as evidence]"
            )
        if provenance == PROVENANCE_POLICY_LAYER:
            return f"[Procedure · {provenance}]\n{content}"
        if provenance == "audit-preview":
            return f"[Decision pattern · audit-preview]\n{content}"
        return content

    def build_preamble(self, *, profile: TurnProfile, decision: ArbitrationDecision) -> str:
        if str(profile.thinking_mode or "precision").lower() == "emergent":
            return (
                "Expert/style layers are expressive guides, NOT factual sources. "
                "Label facts vs emergent inference explicitly.\n"
            )
        return (
            "Style and persona layers are expressive guides, NOT factual sources. "
            "Do not cite style/persona content as evidence of what happened or what someone believes.\n"
        )

    def apply(self, memory_layer: str, *, request: SCPRequest, decision: ArbitrationDecision) -> str:
        """Attach preamble when synthetic slots are present."""
        has_synthetic = any(
            c.dimension in (DIMENSION_STYLE, DIMENSION_PERSONA_SUMMARY, DIMENSION_PROCEDURE)
            for c in list(decision.prompt_plan.items) + list(decision.recall_plan.items)
        )
        if not has_synthetic:
            return memory_layer
        preamble = self.build_preamble(profile=request.turn_profile, decision=decision)
        body = str(memory_layer or "").strip()
        if not body:
            return preamble
        return f"{preamble}\n\n---\n\n{body}"
