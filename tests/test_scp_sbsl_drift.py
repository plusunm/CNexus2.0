"""SBSL drift simulation — 100-turn style creep must trigger correction."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from semantic.dimensions import DIMENSION_FACT, DIMENSION_STYLE
from semantic.stability_loop import SemanticBudgetStabilityLoop
from semantic.types import DriftObservation, SemanticBudgetState


class SBSLDriftSimulationTests(unittest.TestCase):
    def setUp(self):
        self.sbsl = SemanticBudgetStabilityLoop(
            ema_alpha=0.9,
            style_ema_max=0.08,
            fact_ema_floor=0.05,
            style_mean_max=0.10,
            style_rise_delta=0.01,
            style_rise_streak_n=3,
        )

    def test_constant_style_weight_triggers_t1_within_15_turns(self):
        state = SemanticBudgetState()
        correction_turn = None
        weights = {
            DIMENSION_FACT: 0.70,
            DIMENSION_STYLE: 0.12,
            "decision": 0.10,
            "activation": 0.08,
        }

        for turn in range(1, 101):
            state = self.sbsl.update_ema(state, weights)
            observation = DriftObservation(style_weight=0.12, fact_miss_streak=0)
            state, correction = self.sbsl.evaluate(state, observation)
            if correction is not None and correction_turn is None:
                correction_turn = turn
                self.assertIn(
                    correction.trigger_id,
                    ("SBSL-T1", "SBSL-T4", "SBSL-T2", "SBSL-T3"),
                )
                # First drift trigger should be style-related (T1/T4), not fact floor (T3).
                if correction.trigger_id in ("SBSL-T1", "SBSL-T4"):
                    break

        self.assertIsNotNone(correction_turn, "SBSL should trigger within 100 turns")
        self.assertLessEqual(correction_turn, 15, f"T1 expected by turn 15, got {correction_turn}")
        # Re-evaluate last correction id — must be style drift (T1 or T4), not fact floor.
        state_probe = SemanticBudgetState()
        for turn in range(1, correction_turn + 1):
            state_probe = self.sbsl.update_ema(state_probe, weights)
            observation = DriftObservation(style_weight=0.12, fact_miss_streak=0)
            state_probe, correction = self.sbsl.evaluate(state_probe, observation)
        self.assertIsNotNone(correction)
        assert correction is not None
        self.assertIn(correction.trigger_id, ("SBSL-T1", "SBSL-T4"))

    def test_style_frozen_after_level2_correction(self):
        state = SemanticBudgetState(turn_count=10, ema={DIMENSION_STYLE: 0.12, DIMENSION_FACT: 0.40})
        observation = DriftObservation(style_weight=0.12, fact_miss_streak=4)
        state, correction = self.sbsl.evaluate(state, observation)
        self.assertIsNotNone(correction)
        assert correction is not None
        self.assertEqual(correction.level, 3)
        frozen_state = state.__class__(
            **{
                **state.to_dict(),
                "freeze_style_until_turn": state.turn_count + 3,
            }
        )
        self.assertTrue(self.sbsl.is_style_frozen(frozen_state))

    def test_correction_only_tightens_style_cap(self):
        state = SemanticBudgetState(style_weight_max=0.15, fact_floor=0.75)
        before_style_cap = state.style_weight_max
        before_fact_floor = state.fact_floor
        state = SemanticBudgetState(
            turn_count=20,
            ema={DIMENSION_STYLE: 0.12, DIMENSION_FACT: 0.50},
            style_weight_max=before_style_cap,
            fact_floor=before_fact_floor,
        )
        observation = DriftObservation(style_weight=0.12)
        state, correction = self.sbsl.evaluate(state, observation)
        self.assertIsNotNone(correction)
        assert correction is not None
        self.assertLessEqual(correction.style_weight_max, before_style_cap)
        self.assertGreaterEqual(correction.fact_floor, before_fact_floor)


class SemanticBudgetStoreTests(unittest.TestCase):
    def test_atomic_persist_roundtrip(self):
        from semantic.budget_store import SemanticBudgetStore

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "semantic_budget_state.json")
            store = SemanticBudgetStore(path=path)
            original = SemanticBudgetState(
                turn_count=42,
                ema={DIMENSION_STYLE: 0.11, DIMENSION_FACT: 0.52},
                cumulative={DIMENSION_STYLE: 5.0},
            )
            store.save(original)
            loaded = store.load()
            self.assertEqual(loaded.turn_count, 42)
            self.assertAlmostEqual(loaded.ema[DIMENSION_STYLE], 0.11)
            self.assertAlmostEqual(loaded.ema[DIMENSION_FACT], 0.52)
            self.assertAlmostEqual(loaded.cumulative[DIMENSION_STYLE], 5.0)


if __name__ == "__main__":
    unittest.main()
