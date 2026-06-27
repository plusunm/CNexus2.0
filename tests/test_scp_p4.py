"""SCP P4 — PR gate: 100-turn creep, persist recovery, pipeline no-bypass."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
KERNEL_DIR = os.path.join(SRC, "kernel")
GATEWAY_DIR = os.path.join(SRC, "gateway")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from semantic.arbitration import SemanticArbitrationLayer
from semantic.budget_store import SemanticBudgetStore
from semantic.dimensions import DIMENSION_FACT, DIMENSION_STYLE
from semantic.pr_gate import (
    assert_correction_only_tightens,
    assert_sal_invariants,
    run_scp_admit_creep,
    simulate_style_creep,
)
from semantic.scp import SemanticControlPlane
from semantic.stability_loop import SemanticBudgetStabilityLoop
from semantic.types import SCPRequest, SemanticBudgetState, TurnProfile


class SCPPRGateTests(unittest.TestCase):
    def test_pr_gate_simulate_style_creep(self):
        sbsl = SemanticBudgetStabilityLoop(
            ema_alpha=0.9,
            style_ema_max=0.08,
            fact_ema_floor=0.05,
            style_mean_max=0.10,
        )
        turn, _, correction = simulate_style_creep(sbsl, max_trigger_turn=15)
        self.assertLessEqual(turn, 15)
        self.assertIn(correction.trigger_id, ("SBSL-T1", "SBSL-T4"))

    def test_scp_admit_creep_gate_with_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "semantic_budget_state.json")
            store = SemanticBudgetStore(path=path)
            sbsl = SemanticBudgetStabilityLoop(
                ema_alpha=0.9,
                style_ema_max=0.08,
                fact_ema_floor=0.05,
                style_mean_max=0.10,
            )
            scp = SemanticControlPlane(store=store, sbsl=sbsl, persist=True)
            turn, state, correction = run_scp_admit_creep(scp, max_trigger_turn=15)
            self.assertLessEqual(turn, 15)
            self.assertIn(correction.trigger_id, ("SBSL-T1", "SBSL-T4"))

            reloaded = store.load()
            self.assertEqual(reloaded.turn_count, state.turn_count)
            self.assertAlmostEqual(reloaded.ema[DIMENSION_STYLE], state.ema[DIMENSION_STYLE], places=4)

    def test_sal_weights_normalized(self):
        sal = SemanticArbitrationLayer()
        request = SCPRequest(
            query="test",
            turn_profile=TurnProfile(expert_mode="expert:alice", style_source="prompt"),
            prompt_candidates=[],
            recall_candidates=[],
        )
        decision = sal.arbitrate(request)
        assert_sal_invariants(decision.dimension_weights)
        self.assertAlmostEqual(sum(decision.dimension_weights.values()), 1.0)

    def test_correction_only_tightens_caps(self):
        sbsl = SemanticBudgetStabilityLoop(ema_alpha=0.9, style_ema_max=0.08, fact_ema_floor=0.05)
        before = SemanticBudgetState(style_weight_max=0.15, fact_floor=0.75)
        state = SemanticBudgetState(
            turn_count=20,
            ema={DIMENSION_STYLE: 0.12, DIMENSION_FACT: 0.50},
            style_weight_max=0.15,
            fact_floor=0.75,
        )
        from semantic.types import DriftObservation

        after, correction = sbsl.evaluate(state, DriftObservation(style_weight=0.12))
        self.assertIsNotNone(correction)
        assert_correction_only_tightens(before, after, correction)


class PipelineSCPNoBypassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util

        pkg = "cnexus_gateway"
        if pkg not in sys.modules:
            init = os.path.join(GATEWAY_DIR, "__init__.py")
            spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
            module = importlib.util.module_from_spec(spec)
            sys.modules[pkg] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)

        def _load(name, path, package):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = package
            sys.modules[name] = mod
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            return mod

        cls.state_mod = _load(f"{pkg}.state", os.path.join(GATEWAY_DIR, "state.py"), pkg)
        cls.pipeline_mod = _load("kernel.pipeline", os.path.join(KERNEL_DIR, "pipeline.py"), "kernel")

    def _base_deps(self, **overrides):
        from kernel.pipeline import PipelineDeps

        defaults = dict(
            observe=lambda *a, **k: {},
            cognize=lambda *a, **k: {},
            decide=lambda *a, **k: {"intent": "converse"},
            speak=lambda *a, **k: {"text": "ok"},
            converse_mode_profile=lambda _mode: {
                "mode": "fast",
                "inject_memory": True,
                "thinking_mode": "precision",
            },
            thinking_params=lambda _mode: {},
            touch_activity=lambda: None,
            resolve_model=lambda _id: {"id": "cnexus-local", "provider": "cnexus", "enabled": True},
            threshold_activated_fragments=lambda **k: [],
            format_activation_context=lambda *a, **k: "RAW_ACTIVATION_LAYER",
            compose_llm_context=lambda mem="": f"BYPASS::{mem}",
            runtime_context=lambda: "",
            memory_recall=lambda _text, _scope="local": {"context": ""},
            negotiation_conflict_context=lambda: None,
            record_emergent_block_refs=lambda: None,
            should_use_external_llm=lambda _row: False,
            iter_external_llm_stream=lambda *a, **k: iter([]),
            invoke_external_llm=lambda *a, **k: {},
            audit_thinking=lambda *a, **k: None,
            speech_text=lambda spk: "ok",
            persist_turn=lambda _p: None,
            fast_converse=True,
        )
        defaults.update(overrides)
        return PipelineDeps(**defaults)

    def test_prepare_turn_uses_scp_context_not_bypass(self):
        budget = SemanticBudgetState()

        def scp_admit(_text, _ctx, _profile):
            return SimpleNamespace(
                llm_context="SCP::controlled",
                admitted=True,
                budget_state=budget,
                correction=None,
                observation=SimpleNamespace(triggers=[]),
            )

        emotion = SimpleNamespace(val=0.0, arousal=0.0, dominance=0.0)
        engine = {
            "consolidation": {},
            "current_iteration": 0,
            "state": SimpleNamespace(emotion=emotion),
            "memory_store": {"blocks": []},
            "trace": [],
        }
        deps = self._base_deps(scp_admit=scp_admit)
        pipeline = self.pipeline_mod.CognitivePipeline(self.state_mod.EngineStateManager(engine), deps)
        prep = pipeline.prepare_turn("hi", None, converse_mode="fast")
        self.assertEqual(prep["llm_context"], "SCP::controlled")
        self.assertNotIn("BYPASS::", prep["llm_context"])

    def test_empty_scp_context_does_not_bypass(self):
        budget = SemanticBudgetState()

        def scp_admit(_text, _ctx, _profile):
            return SimpleNamespace(
                llm_context="",
                admitted=True,
                budget_state=budget,
                correction=None,
                observation=SimpleNamespace(triggers=[]),
            )

        emotion = SimpleNamespace(val=0.0, arousal=0.0, dominance=0.0)
        engine = {
            "consolidation": {},
            "current_iteration": 0,
            "state": SimpleNamespace(emotion=emotion),
            "memory_store": {"blocks": []},
            "trace": [],
        }
        deps = self._base_deps(scp_admit=scp_admit)
        pipeline = self.pipeline_mod.CognitivePipeline(self.state_mod.EngineStateManager(engine), deps)
        prep = pipeline.prepare_turn("hi", None, converse_mode="fast")
        self.assertEqual(prep["llm_context"], "")
        self.assertNotIn("RAW_ACTIVATION", prep["llm_context"])


if __name__ == "__main__":
    unittest.main()
