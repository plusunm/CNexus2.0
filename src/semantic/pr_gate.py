"""SCP PR gate helpers — freeze checks for P0–P4 (spec §11)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional, Tuple

from .dimensions import DIMENSION_ACTIVATION, DIMENSION_DECISION, DIMENSION_FACT, DIMENSION_STYLE, normalize_weights
from .stability_loop import SemanticBudgetStabilityLoop
from .types import DriftObservation, SCPRequest, SemanticBudgetState, TurnProfile


def simulate_style_creep(
    sbsl: SemanticBudgetStabilityLoop,
    *,
    turns: int = 100,
    style_weight: float = 0.12,
    fact_weight: float = 0.70,
    max_trigger_turn: int = 15,
) -> Tuple[int, SemanticBudgetState, Any]:
    """
    100-turn constant style creep — must fire SBSL-T1/T4 within max_trigger_turn.
    Returns (correction_turn, final_state, correction).
    """
    state = SemanticBudgetState()
    weights = normalize_weights(
        {
            DIMENSION_FACT: fact_weight,
            DIMENSION_STYLE: style_weight,
            DIMENSION_DECISION: 0.10,
            DIMENSION_ACTIVATION: 0.08,
        }
    )
    correction_turn = 0
    last_correction = None

    for turn in range(1, turns + 1):
        state = sbsl.update_ema(state, weights)
        observation = DriftObservation(style_weight=style_weight, fact_miss_streak=0)
        state, correction = sbsl.evaluate(state, observation)
        if correction is not None and correction_turn == 0:
            correction_turn = turn
            last_correction = correction
            if correction.trigger_id in ("SBSL-T1", "SBSL-T4"):
                break

    if correction_turn == 0 or correction_turn > max_trigger_turn:
        raise AssertionError(
            f"SBSL creep gate failed: correction_turn={correction_turn}, expected ≤{max_trigger_turn}"
        )
    if last_correction is None:
        raise AssertionError("SBSL creep gate failed: no correction emitted")
    if last_correction.trigger_id not in ("SBSL-T1", "SBSL-T4", "SBSL-T2", "SBSL-T3", "SBSL-T5"):
        raise AssertionError(f"unexpected trigger {last_correction.trigger_id}")

    return correction_turn, state, last_correction


def assert_sal_invariants(dimension_weights: Dict[str, float], *, style_tol: float = 1e-6) -> None:
    total = sum(float(v) for v in dimension_weights.values())
    if abs(total - 1.0) > style_tol:
        raise AssertionError(f"Σw must be 1.0, got {total}")


def assert_correction_only_tightens(
    before: SemanticBudgetState,
    after: SemanticBudgetState,
    correction,
) -> None:
    if correction is None:
        return
    if float(after.style_weight_max) > float(before.style_weight_max) + 1e-9:
        raise AssertionError("SCP-08 violated: style_weight_max increased")
    if float(after.fact_floor) < float(before.fact_floor) - 1e-9:
        raise AssertionError("SCP-08 violated: fact_floor decreased")


class _CreepWeightSAL:
    """Test-only SAL shim — pins style EMA feed for end-to-end SCP creep simulation."""

    def __init__(self, inner: Any, *, style_weight: float = 0.12):
        self._inner = inner
        self._style_weight = style_weight

    def arbitrate(self, request: SCPRequest):
        decision = self._inner.arbitrate(request)
        weights = normalize_weights(
            {
                DIMENSION_FACT: 0.70,
                DIMENSION_STYLE: self._style_weight,
                DIMENSION_DECISION: 0.10,
                DIMENSION_ACTIVATION: 0.08,
            }
        )
        return replace(decision, dimension_weights=weights, violations=[])


def run_scp_admit_creep(
    scp_plane: Any,
    *,
    turns: int = 100,
    style_weight: float = 0.12,
    max_trigger_turn: int = 15,
) -> Tuple[int, SemanticBudgetState, Any]:
    """Drive SCP.admit() for N turns with pinned style weights; enforce creep gate."""
    from .arbitration import SemanticArbitrationLayer
    from .scp import SemanticControlPlane

    if not isinstance(scp_plane, SemanticControlPlane):
        raise TypeError("scp_plane must be SemanticControlPlane")

    creep_sal = _CreepWeightSAL(SemanticArbitrationLayer(), style_weight=style_weight)
    scp = SemanticControlPlane(
        store=scp_plane._store,
        sal=creep_sal,
        composer=scp_plane._composer,
        observer=scp_plane._observer,
        sbsl=scp_plane._sbsl,
        persist=scp_plane._persist,
    )
    sbsl: SemanticBudgetStabilityLoop = scp._sbsl

    correction_turn = 0
    last_correction = None
    state = scp.load_budget_state()

    for turn in range(1, turns + 1):
        request = SCPRequest(
            query=f"creep-turn-{turn}",
            turn_profile=TurnProfile(expert_mode="expert:test"),
            activation_context="OS memory baseline",
            budget_state=state,
            compose_llm_context=lambda mem: f"CTX::{mem}",
        )
        response = scp.admit(request)
        assert_sal_invariants(response.decision.dimension_weights)
        before_caps = SemanticBudgetState(
            style_weight_max=state.style_weight_max,
            fact_floor=state.fact_floor,
        )
        state = response.budget_state
        if response.correction is not None and correction_turn == 0:
            correction_turn = turn
            last_correction = response.correction
            assert_correction_only_tightens(before_caps, state, response.correction)
            if response.correction.trigger_id in ("SBSL-T1", "SBSL-T4"):
                break

    if correction_turn == 0 or correction_turn > max_trigger_turn:
        raise AssertionError(
            f"SCP admit creep gate failed: correction_turn={correction_turn}, expected ≤{max_trigger_turn}"
        )
    if last_correction is None:
        raise AssertionError("SCP admit creep gate failed: no correction")
    return correction_turn, state, last_correction
