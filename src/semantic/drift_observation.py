"""Turn-level drift observation (SCP L4) — feeds SBSL triggers."""

from __future__ import annotations

import os

from .dimensions import DIMENSION_FACT, DIMENSION_STYLE, entanglement_score
from .types import ArbitrationDecision, DriftObservation, SCPRequest

_OVERLAP_WARN = float(os.environ.get("CNEXUS_SCP_OVERLAP_WARN", "0.30"))


class DriftObserver:
    """Turn observer — spatial drift signals before SBSL temporal loop."""

    def observe(self, request: SCPRequest, decision: ArbitrationDecision) -> DriftObservation:
        style_weight = float(decision.dimension_weights.get(DIMENSION_STYLE, 0.0))
        fact_hits = int(request.fact_hits)
        overlap = _cross_path_overlap(request, decision)
        triggers: list[str] = []

        if overlap >= _OVERLAP_WARN:
            triggers.append("DRIFT-OVERLAP")
        if decision.violations:
            triggers.extend(f"DRIFT-{v.upper()}" for v in decision.violations)
        if fact_hits <= 0 and request.turn_profile.expert_mode:
            triggers.append("DRIFT-FACT-MISS")

        ent_score = entanglement_score(request.budget_state.ema) if request.budget_state.ema else style_weight
        dual_risk = overlap >= _OVERLAP_WARN or bool(decision.violations)

        fact_miss_streak = 0
        if fact_hits <= 0:
            fact_miss_streak = int(request.budget_state.fact_miss_streak) + 1

        return DriftObservation(
            cross_path_overlap_ratio=overlap,
            style_weight=style_weight,
            fact_miss_streak=fact_miss_streak,
            triggers=triggers,
            entanglement_score=ent_score,
            dual_path_risk=dual_risk,
        )


def _cross_path_overlap(request: SCPRequest, decision: ArbitrationDecision) -> float:
    recall_text = " ".join(c.content for c in decision.recall_plan.items if c.content).strip().lower()
    prompt_text = " ".join(c.content for c in decision.prompt_plan.items if c.content).strip().lower()
    if not recall_text or not prompt_text:
        return 0.0
    recall_tokens = set(recall_text.split())
    prompt_tokens = set(prompt_text.split())
    if not recall_tokens or not prompt_tokens:
        return 0.0
    inter = len(recall_tokens & prompt_tokens)
    union = len(recall_tokens | prompt_tokens)
    return inter / union if union else 0.0
