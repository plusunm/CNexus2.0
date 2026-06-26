"""Fast converse prepare path tests."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
KERNEL_DIR = os.path.join(SRC, "kernel")
GATEWAY_DIR = os.path.join(SRC, "gateway")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load(name, path, package):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class FastConversePrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pkg = "cnexus_gateway"
        if pkg not in sys.modules:
            init = os.path.join(GATEWAY_DIR, "__init__.py")
            spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
            module = importlib.util.module_from_spec(spec)
            sys.modules[pkg] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
        cls.state_mod = _load(f"{pkg}.state", os.path.join(GATEWAY_DIR, "state.py"), pkg)
        cls.pipeline_mod = _load("kernel.pipeline", os.path.join(KERNEL_DIR, "pipeline.py"), "kernel")

    def test_fast_converse_skips_activation_scan(self):
        calls = {"activation": 0, "resolve": 0}

        class Emotion:
            val = arousal = dominance = 0.0

        class St:
            emotion = Emotion()

        engine = {
            "consolidation": {},
            "current_iteration": 0,
            "state": St(),
            "memory_store": {"blocks": []},
            "trace": [],
        }
        from kernel.pipeline import PipelineDeps

        deps = PipelineDeps(
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
            resolve_model=lambda _id: (calls.__setitem__("resolve", calls["resolve"] + 1) or {"id": "cnexus-local", "provider": "cnexus", "enabled": True}),
            threshold_activated_fragments=lambda **k: (calls.__setitem__("activation", calls["activation"] + 1) or []),
            format_activation_context=lambda *a, **k: "",
            compose_llm_context=lambda mem="": mem,
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
        state = self.state_mod.EngineStateManager(engine)
        pipeline = self.pipeline_mod.CognitivePipeline(state, deps)
        prep = pipeline.prepare_turn("hi", None, converse_mode="fast")
        self.assertEqual(calls["activation"], 0)
        self.assertEqual(calls["resolve"], 1)
        self.assertEqual(prep["activation_hits"], [])


if __name__ == "__main__":
    unittest.main()
