"""SCP P0 pass-through — zero diff when disabled; identical compose when enabled."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
KERNEL_DIR = os.path.join(SRC, "kernel")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from semantic.scp import SemanticControlPlane, scp_enabled
from semantic.types import SCPRequest, TurnProfile


class SCPPassThroughTests(unittest.TestCase):
    def test_scp_disabled_by_default(self):
        env = os.environ.get("CNEXUS_SCP_ENABLED")
        try:
            os.environ.pop("CNEXUS_SCP_ENABLED", None)
            self.assertFalse(scp_enabled())
        finally:
            if env is not None:
                os.environ["CNEXUS_SCP_ENABLED"] = env

    def test_admit_pass_through_preserves_compose(self):
        memory = "activation snippet\n---\nrecall snippet"
        runtime_prefix = "RUNTIME"

        def compose(mem: str = "") -> str:
            parts = [runtime_prefix, mem.strip()]
            return "\n\n---\n\n".join(p for p in parts if p)

        scp = SemanticControlPlane(persist=False)
        request = SCPRequest(
            query="hello",
            turn_profile=TurnProfile(),
            activation_context=memory,
            compose_llm_context=compose,
        )
        response = scp.admit(request)
        self.assertTrue(response.admitted)
        expected = compose(memory)
        self.assertEqual(response.llm_context, expected)

    def test_sal_excludes_dual_style_on_prompt_source(self):
        from semantic.arbitration import SemanticArbitrationLayer
        from semantic.types import SemanticCandidate

        sal = SemanticArbitrationLayer()
        request = SCPRequest(
            query="q",
            turn_profile=TurnProfile(style_source="prompt"),
            recall_candidates=[
                SemanticCandidate(block_id="r1", dimension="style", content="write like X", source="recall"),
                SemanticCandidate(block_id="r2", dimension="fact", content="fact A", source="recall"),
            ],
            prompt_candidates=[
                SemanticCandidate(block_id="p1", dimension="style", content="tone formal", source="prompt"),
            ],
        )
        decision = sal.arbitrate(request)
        recall_dims = {c.dimension for c in decision.recall_plan.items}
        self.assertNotIn("style", recall_dims)
        self.assertTrue(any(c.dimension == "style" for c in decision.prompt_plan.items))
        self.assertTrue(any(ex.reason == "sss_single_source" for ex in decision.exclusions))


class SCPPipelineHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util

        gateway_dir = os.path.join(SRC, "gateway")
        pkg = "cnexus_gateway_scp_test"
        if pkg not in sys.modules:
            init = os.path.join(gateway_dir, "__init__.py")
            spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[gateway_dir])
            module = importlib.util.module_from_spec(spec)
            sys.modules[pkg] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)

        def _load(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = pkg
            sys.modules[name] = mod
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            return mod

        cls.state_mod = _load(f"{pkg}.state", os.path.join(gateway_dir, "state.py"))
        spec = importlib.util.spec_from_file_location("kernel.pipeline", os.path.join(KERNEL_DIR, "pipeline.py"))
        cls.pipeline_mod = importlib.util.module_from_spec(spec)
        cls.pipeline_mod.__package__ = "kernel"
        sys.modules["kernel.pipeline"] = cls.pipeline_mod
        assert spec.loader is not None
        spec.loader.exec_module(cls.pipeline_mod)

    def test_pipeline_without_scp_uses_compose_directly(self):
        PipelineDeps = self.pipeline_mod.PipelineDeps
        calls = {"compose": 0}

        def compose(mem: str = "") -> str:
            calls["compose"] += 1
            return f"CTX:{mem}"

        class St:
            class emotion:
                val = arousal = dominance = 0.0

        engine = {
            "consolidation": {},
            "current_iteration": 0,
            "state": St(),
            "memory_store": {"blocks": []},
            "trace": [],
        }
        state = self.state_mod.EngineStateManager(engine)
        deps = PipelineDeps(
            observe=lambda *a, **k: {},
            cognize=lambda *a, **k: type("C", (), {"context": {}})(),
            decide=lambda *a, **k: {},
            speak=lambda *a, **k: {},
            converse_mode_profile=lambda _m: {
                "mode": "deep",
                "inject_memory": True,
                "use_recall_supplement": False,
                "thinking_mode": "precision",
            },
            thinking_params=lambda _m: {},
            touch_activity=lambda: None,
            resolve_model=lambda _id: {"id": "local", "provider": "cnexus", "enabled": True},
            threshold_activated_fragments=lambda **k: [],
            format_activation_context=lambda *a, **k: "MEM",
            compose_llm_context=compose,
            runtime_context=lambda: "",
            memory_recall=lambda *a, **k: {"context": ""},
            negotiation_conflict_context=lambda: None,
            record_emergent_block_refs=lambda: None,
            should_use_external_llm=lambda _r: False,
            iter_external_llm_stream=lambda *a, **k: iter([]),
            invoke_external_llm=lambda *a, **k: {},
            audit_thinking=lambda *a, **k: None,
            speech_text=lambda _s: "ok",
            persist_turn=lambda _p: None,
            fast_converse=False,
        )
        pipeline = self.pipeline_mod.CognitivePipeline(state, deps)
        prep = pipeline.prepare_turn("hi", None, converse_mode="deep")
        self.assertEqual(prep["llm_context"], "CTX:MEM")
        self.assertEqual(calls["compose"], 1)


if __name__ == "__main__":
    unittest.main()
