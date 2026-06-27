"""Context Composer — slot isolation + cross-path dedupe (SCP L2)."""

from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Set, Tuple

from .dimensions import (
    DIMENSION_ACTIVATION,
    DIMENSION_DECISION,
    DIMENSION_FACT,
    DIMENSION_PERSONA_SUMMARY,
    DIMENSION_PROCEDURE,
    DIMENSION_STYLE,
    dominance,
)
from .provenance_gate import ProvenanceGate
from .types import ArbitrationDecision, SCPRequest, SemanticCandidate

_SLOT_ORDER = (
    "expert_procedure",
    "expert_style",
    "memory_evidence",
    "activation_graph",
    "os_memory",
)


class ContextComposer:
    """Assemble LLM memory layer from isolated slots — no dual-path resonance."""

    def __init__(self, *, provenance: ProvenanceGate | None = None):
        self._provenance = provenance or ProvenanceGate()

    def compose(self, request: SCPRequest, decision: ArbitrationDecision) -> str:
        os_layer = str(request.activation_context or "").strip()
        prompt_items = list(decision.prompt_plan.items)
        recall_items = list(decision.recall_plan.items)
        activation_items = list(decision.activation_plan.items)

        if not prompt_items and not recall_items and not activation_items:
            return os_layer

        excluded = _collect_block_ids(prompt_items)
        recall_items = [c for c in recall_items if c.block_id not in excluded]
        recall_items, prompt_items = _dedupe_cross_path(recall_items, prompt_items)

        slots: Dict[str, str] = {}
        procedure = _join_candidates(
            [c for c in prompt_items if c.dimension == DIMENSION_PROCEDURE],
            request,
            self._provenance,
        )
        if procedure:
            slots["expert_procedure"] = procedure

        style_items = [c for c in prompt_items if c.dimension == DIMENSION_STYLE]
        if request.turn_profile.style_source == "recall":
            style_items = [c for c in recall_items if c.dimension == DIMENSION_STYLE]
        style = _join_candidates(style_items, request, self._provenance)
        if style:
            slots["expert_style"] = style

        evidence_items = [
            c
            for c in recall_items
            if c.dimension in (DIMENSION_FACT, DIMENSION_DECISION)
        ]
        evidence = _join_candidates(evidence_items, request, self._provenance)
        if evidence:
            slots["memory_evidence"] = evidence

        activation = _join_candidates(
            activation_items
            or [c for c in recall_items if c.dimension == DIMENSION_ACTIVATION],
            request,
            self._provenance,
        )
        if activation:
            slots["activation_graph"] = activation

        if os_layer:
            slots["os_memory"] = os_layer

        if len(slots) <= 1 and "os_memory" in slots:
            return os_layer

        parts: List[str] = []
        labels = {
            "expert_procedure": "Expert Procedure",
            "expert_style": "Expert Style (not fact)",
            "memory_evidence": "Memory Evidence",
            "activation_graph": "Activation Graph",
            "os_memory": "Subconscious Memory",
        }
        for key in _SLOT_ORDER:
            body = slots.get(key, "").strip()
            if body:
                parts.append(f"--- {labels[key]} ---\n{body}")
        return "\n\n".join(parts)


def _collect_block_ids(items: Iterable[SemanticCandidate]) -> Set[str]:
    return {str(c.block_id) for c in items if c.block_id}


def _content_key(candidate: SemanticCandidate) -> str:
    if candidate.content_hash:
        return candidate.content_hash
    normalized = re.sub(r"\s+", " ", str(candidate.content or "").strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _dedupe_cross_path(
    recall_items: List[SemanticCandidate],
    prompt_items: List[SemanticCandidate],
) -> Tuple[List[SemanticCandidate], List[SemanticCandidate]]:
    seen: Set[str] = set()
    kept_recall: List[SemanticCandidate] = []
    for item in recall_items:
        key = _content_key(item)
        if key in seen:
            continue
        seen.add(key)
        kept_recall.append(item)

    kept_prompt: List[SemanticCandidate] = []
    for item in prompt_items:
        key = _content_key(item)
        overlap = [r for r in kept_recall if _content_key(r) == key]
        if overlap:
            winner = dominance(overlap[0].dimension, item.dimension)
            if winner != item.dimension:
                continue
        if key in seen and not overlap:
            continue
        seen.add(key)
        kept_prompt.append(item)
    return kept_recall, kept_prompt


def _join_candidates(
    items: List[SemanticCandidate],
    request: SCPRequest,
    gate: ProvenanceGate,
) -> str:
    lines: List[str] = []
    for item in items:
        formatted = gate.format_candidate(item, profile=request.turn_profile)
        if formatted:
            lines.append(formatted)
    return "\n---\n".join(lines)
