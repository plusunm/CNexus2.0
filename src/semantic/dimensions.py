"""Semantic dimension registry and dominance ordering (SSS-04)."""

from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

DIMENSION_FACT = "fact"
DIMENSION_DECISION = "decision"
DIMENSION_ACTIVATION = "activation"
DIMENSION_STYLE = "style"
DIMENSION_PERSONA_SUMMARY = "persona_summary"
DIMENSION_PROCEDURE = "procedure"

ALL_DIMENSIONS: FrozenSet[str] = frozenset(
    {
        DIMENSION_FACT,
        DIMENSION_DECISION,
        DIMENSION_ACTIVATION,
        DIMENSION_STYLE,
        DIMENSION_PERSONA_SUMMARY,
        DIMENSION_PROCEDURE,
    }
)

# Higher rank wins in dominance resolution (SSS-04).
DOMINANCE_RANK: Dict[str, int] = {
    DIMENSION_FACT: 5,
    DIMENSION_DECISION: 4,
    DIMENSION_ACTIVATION: 3,
    DIMENSION_STYLE: 2,
    DIMENSION_PERSONA_SUMMARY: 1,
    DIMENSION_PROCEDURE: 0,
}

PRIMARY_SOURCE: Dict[str, str] = {
    DIMENSION_FACT: "recall",
    DIMENSION_DECISION: "recall",
    DIMENSION_ACTIVATION: "recall",
    DIMENSION_STYLE: "prompt_or_recall",
    DIMENSION_PERSONA_SUMMARY: "prompt",
    DIMENSION_PROCEDURE: "prompt",
}


def dominance(a: str, b: str) -> str:
    """Return the dimension with higher dominance rank."""
    ra = DOMINANCE_RANK.get(a, -1)
    rb = DOMINANCE_RANK.get(b, -1)
    return a if ra >= rb else b


def default_turn_weights(*, precision: bool = True) -> Dict[str, float]:
    """Baseline per-turn weights when no expert injection is active."""
    if precision:
        return {
            DIMENSION_FACT: 0.55,
            DIMENSION_DECISION: 0.25,
            DIMENSION_ACTIVATION: 0.15,
            DIMENSION_STYLE: 0.05,
            DIMENSION_PERSONA_SUMMARY: 0.0,
            DIMENSION_PROCEDURE: 0.0,
        }
    return {
        DIMENSION_FACT: 0.40,
        DIMENSION_DECISION: 0.20,
        DIMENSION_ACTIVATION: 0.15,
        DIMENSION_STYLE: 0.15,
        DIMENSION_PERSONA_SUMMARY: 0.05,
        DIMENSION_PROCEDURE: 0.05,
    }


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total <= 0:
        return default_turn_weights()
    return {k: max(0.0, float(v)) / total for k, v in weights.items()}


def entanglement_score(ema: Dict[str, float]) -> float:
    """Higher = more style-drift / less fact anchor."""
    style = float(ema.get(DIMENSION_STYLE, 0.0))
    fact = float(ema.get(DIMENSION_FACT, 0.0))
    return style - fact
