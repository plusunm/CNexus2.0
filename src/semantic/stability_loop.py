"""Semantic Budget Stability Loop (SBSL) — long-term drift correction (SCP L5)."""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Dict, Optional, Tuple

from .dimensions import DIMENSION_FACT, DIMENSION_STYLE, entanglement_score, normalize_weights
from .types import BudgetCorrection, DriftObservation, SemanticBudgetState


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class SemanticBudgetStabilityLoop:
    """EMA tracking + restoration policy (SCP-06..08)."""

    def __init__(
        self,
        *,
        ema_alpha: Optional[float] = None,
        style_ema_max: Optional[float] = None,
        fact_ema_floor: Optional[float] = None,
        style_mean_max: Optional[float] = None,
        style_rise_delta: Optional[float] = None,
        style_rise_streak_n: Optional[int] = None,
    ):
        self.ema_alpha = ema_alpha if ema_alpha is not None else _env_float("CNEXUS_SBS_EMA_ALPHA", 0.9)
        self.style_ema_max = style_ema_max if style_ema_max is not None else _env_float("CNEXUS_SBS_STYLE_EMA_MAX", 0.08)
        self.fact_ema_floor = fact_ema_floor if fact_ema_floor is not None else _env_float("CNEXUS_SBS_FACT_EMA_FLOOR", 0.45)
        self.style_mean_max = style_mean_max if style_mean_max is not None else _env_float("CNEXUS_SBS_STYLE_MEAN_MAX", 0.10)
        self.style_rise_delta = style_rise_delta if style_rise_delta is not None else _env_float("CNEXUS_SBS_STYLE_RISE_DELTA", 0.01)
        self.style_rise_streak_n = style_rise_streak_n if style_rise_streak_n is not None else _env_int("CNEXUS_SBS_STYLE_RISE_STREAK_N", 3)

    def update_ema(self, state: SemanticBudgetState, weights: Dict[str, float]) -> SemanticBudgetState:
        alpha = self.ema_alpha
        ema = dict(state.ema)
        cumulative = dict(state.cumulative)
        for dim, weight in normalize_weights(weights).items():
            prev = float(ema.get(dim, 0.0))
            ema[dim] = alpha * prev + (1.0 - alpha) * float(weight)
            cumulative[dim] = float(cumulative.get(dim, 0.0)) + float(weight)

        prev_style = float(state.ema.get(DIMENSION_STYLE, state.prev_ema_style))
        new_style = float(ema.get(DIMENSION_STYLE, 0.0))
        rise_streak = state.style_rise_streak
        if new_style > prev_style + self.style_rise_delta:
            rise_streak += 1
        else:
            rise_streak = 0

        return replace(
            state,
            turn_count=int(state.turn_count) + 1,
            ema=ema,
            cumulative=cumulative,
            prev_ema_style=prev_style,
            style_rise_streak=rise_streak,
        )

    def evaluate(
        self,
        state: SemanticBudgetState,
        observation: DriftObservation,
    ) -> Tuple[SemanticBudgetState, Optional[BudgetCorrection]]:
        triggers: list[str] = []
        ema_style = float(state.ema.get(DIMENSION_STYLE, 0.0))
        ema_fact = float(state.ema.get(DIMENSION_FACT, 0.0))
        turns = max(1, int(state.turn_count))
        mean_style = float(state.cumulative.get(DIMENSION_STYLE, 0.0)) / turns

        if ema_style > self.style_ema_max:
            triggers.append("SBSL-T1")
        if state.style_rise_streak >= self.style_rise_streak_n:
            triggers.append("SBSL-T2")
        if ema_fact < self.fact_ema_floor:
            triggers.append("SBSL-T3")
        if mean_style > self.style_mean_max:
            triggers.append("SBSL-T4")
        if observation.fact_miss_streak >= 3 and ema_style > 0.05:
            triggers.append("SBSL-T5")

        if not triggers:
            return replace(state, correction_active=False), None

        before = entanglement_score(state.ema)
        level, correction = self._restoration_policy(triggers, state)
        after_state = replace(
            state,
            correction_active=True,
            last_correction=correction.trigger_id,
            style_weight_max=correction.style_weight_max,
            fact_floor=correction.fact_floor,
            freeze_style_until_turn=correction.freeze_style_until_turn,
        )
        after = entanglement_score(after_state.ema)
        # SCP-08: correction must not increase entanglement on EMA snapshot alone;
        # weight caps apply on subsequent turns.
        if after > before and level < 3:
            correction = replace(correction, level=max(level, 2), style_source_override="off", force_mmr_rebalance=True)
            after_state = replace(after_state, freeze_style_until_turn=max(state.turn_count + 1, state.freeze_style_until_turn))

        observation.triggers = list(triggers)
        return after_state, correction

    def _restoration_policy(self, triggers: list[str], state: SemanticBudgetState) -> Tuple[int, BudgetCorrection]:
        critical = "SBSL-T5" in triggers
        high = critical or "SBSL-T2" in triggers or "SBSL-T3" in triggers
        medium = "SBSL-T1" in triggers or "SBSL-T4" in triggers

        if critical:
            return 3, BudgetCorrection(
                style_weight_max=max(0.03, state.style_weight_max - 0.08),
                fact_floor=min(0.85, state.fact_floor + 0.10),
                style_source_override="off",
                force_mmr_rebalance=True,
                freeze_style_until_turn=state.turn_count + 3,
                trigger_id="SBSL-T5",
                level=3,
            )
        if high:
            return 2, BudgetCorrection(
                style_weight_max=max(0.05, state.style_weight_max - 0.05),
                fact_floor=min(0.80, state.fact_floor + 0.05),
                style_source_override="off",
                force_mmr_rebalance=True,
                freeze_style_until_turn=state.turn_count + 1,
                trigger_id=triggers[0],
                level=2,
            )
        if medium:
            return 1, BudgetCorrection(
                style_weight_max=max(0.05, state.style_weight_max - 0.03),
                fact_floor=min(0.80, state.fact_floor + 0.05),
                style_source_override=None,
                force_mmr_rebalance=False,
                freeze_style_until_turn=0,
                trigger_id=triggers[0],
                level=1,
            )
        return 0, BudgetCorrection(trigger_id="", level=0)

    def apply_correction_to_profile(self, state: SemanticBudgetState, correction: Optional[BudgetCorrection]) -> Dict[str, float]:
        """Budget caps consumed by SAL on the next turn."""
        caps = {
            "style_weight_max": float(state.style_weight_max),
            "fact_floor": float(state.fact_floor),
        }
        if correction is None:
            return caps
        caps["style_weight_max"] = min(caps["style_weight_max"], float(correction.style_weight_max))
        caps["fact_floor"] = max(caps["fact_floor"], float(correction.fact_floor))
        return caps

    def is_style_frozen(self, state: SemanticBudgetState) -> bool:
        return int(state.turn_count) < int(state.freeze_style_until_turn)
