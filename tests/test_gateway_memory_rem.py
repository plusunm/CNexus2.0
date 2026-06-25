"""Tests for MemoryRemService — context assembly and cycle orchestration."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_modules():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    def load(name, relpath):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_mod = load(f"{pkg}.state", "state.py")
    load(f"{pkg}.services.converse_speech", os.path.join("services", "converse_speech.py"))
    load(f"{pkg}.services.converse_thinking", os.path.join("services", "converse_thinking.py"))
    load(f"{pkg}.services.llm", os.path.join("services", "llm.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.wormhole_embed", os.path.join("services", "memory", "wormhole_embed.py"))
    graph_mod = load(f"{pkg}.services.memory.graph", os.path.join("services", "memory", "graph.py"))
    synthesis_mod = load(f"{pkg}.services.memory.rem_synthesis", os.path.join("services", "memory", "rem_synthesis.py"))
    rem_mod = load(f"{pkg}.services.memory.rem", os.path.join("services", "memory", "rem.py"))
    return state_mod, graph_mod, synthesis_mod, rem_mod


class MemoryRemServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.graph_mod, cls.synthesis_mod, cls.rem_mod = _load_modules()

    def _graph(self, engine):
        return self.graph_mod.MemoryGraphService(
            self.state_mod.EngineStateManager(engine),
            self.graph_mod.MemoryGraphHooks(
                extract_keywords=lambda text, limit: [text[:3]] if text else [],
            ),
            config=self.graph_mod.MemoryGraphConfig(wormhole_max_compare=0),
        )

    def _engine(self, **overrides):
        state = type("State", (), {"goal": {"current": "explore", "progress": 0.5}})()
        engine = {
            "memory_store": type("Store", (), {"blocks": []})(),
            "trace": [],
            "consolidation": {},
            "activation": {"scores": {}},
            "projection": {"nodes": {}, "links": []},
            "state": state,
        }
        engine.update(overrides)
        return engine

    def _synthesizer(self):
        return self.synthesis_mod.RemConsolidationSynthesizer(
            self.synthesis_mod.RemConsolidationSynthesisHooks(
                extract_keywords=lambda text, limit: ["kw"],
                resolve_model_row=lambda _model_id: None,
                llm_invoke=lambda _row, _prompt: {"reply": ""},
            ),
        )

    def _rem(self, engine, *, get_rem_engine=lambda: None):
        return self.rem_mod.MemoryRemService(
            self.state_mod.EngineStateManager(engine),
            self._graph(engine),
            self.rem_mod.MemoryRemHooks(
                get_rem_engine=get_rem_engine,
                extract_keywords=lambda text, limit: ["kw"],
                speech_text=lambda speech: str(speech.get("text") or ""),
                append_runtime_log=lambda *a, **k: None,
                schedule_persist=lambda: None,
                get_cognitive_pruning_engine=lambda: None,
            ),
            self._synthesizer(),
        )

    def test_build_context_enriches_trace_reply_text(self):
        engine = self._engine(
            trace=[{"iteration": 1, "input": "hi", "speech": {"text": "hello"}}],
            consolidation={"last_rem_at": 0},
        )
        ctx = self._rem(engine).build_context()
        self.assertEqual(ctx["trace"][0]["reply_text"], "hello")
        self.assertIn("specs", ctx)
        self.assertIs(ctx["consolidation"], engine["consolidation"])

    def test_consolidation_status_disabled_without_engine(self):
        engine = self._engine()
        svc = self._rem(engine)
        status = svc.consolidation_status(engine["consolidation"], svc.build_context())
        self.assertEqual(status, {"enabled": False})

    def test_run_deep_sleep_unavailable_without_engine(self):
        engine = self._engine()
        report = self._rem(engine).run_deep_sleep(force=True)
        self.assertFalse(report["ok"])
        self.assertEqual(report["error"], "rem_engine_unavailable")

    def test_add_semantic_block_via_cycle_callback(self):
        store = type("Store", (), {"blocks": []})()

        def add(block):
            store.blocks.append(block)

        store.add = add
        engine = self._engine(
            memory_store=store,
            consolidation={"last_activity_at": 0, "last_rem_at": 0, "rem_running": False},
        )

        class FakeEngine:
            enabled = True

            def run_rem_cycle(self, ctx, **kwargs):
                kwargs["add_block_fn"]({
                    "block_id": "sem-rem-1-1",
                    "data": {"content": " distilled fact "},
                })
                return {"ok": True}

        svc = self._rem(engine, get_rem_engine=lambda: FakeEngine())
        report = svc.run_deep_sleep(force=True)
        self.assertTrue(report["ok"])
        self.assertEqual(len(store.blocks), 1)
        self.assertEqual(store.blocks[0]["data"]["keywords"], ["kw"])
        self.assertEqual(engine["activation"]["scores"]["sem-rem-1-1"], 1.0)


if __name__ == "__main__":
    unittest.main()
