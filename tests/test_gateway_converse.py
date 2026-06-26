"""Tests for converse event schema and generator safety."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
GATEWAY_DIR = os.path.join(SRC, "gateway")
KERNEL_DIR = os.path.join(SRC, "kernel")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load_module(name: str, path: str, package: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ConverseEventsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events_mod = _load_module(
            "kernel.converse_events",
            os.path.join(KERNEL_DIR, "converse_events.py"),
            "kernel",
        )

    def test_chunk_maps_to_token_sse(self):
        event = self.events_mod.converse_event(self.events_mod.ConverseEventType.CHUNK, "hello")
        raw = self.events_mod.event_to_sse_string(event)
        self.assertIn("event: token", raw)
        payload = json.loads(raw.split("data: ", 1)[1])
        self.assertEqual(payload["text"], "hello")

    def test_error_maps_to_error_sse(self):
        event = self.events_mod.converse_event(self.events_mod.ConverseEventType.ERROR, "boom")
        raw = self.events_mod.event_to_sse_string(event)
        self.assertIn("event: error", raw)

    def test_step_and_causality_in_sse_payload(self):
        event = self.events_mod.converse_event(
            self.events_mod.ConverseEventType.STATUS,
            "Thinking...",
            step="decide",
            causality_id="v2-trace-1",
        )
        raw = self.events_mod.event_to_sse_string(event)
        payload = json.loads(raw.split("data: ", 1)[1])
        self.assertEqual(payload["step"], "decide")
        self.assertEqual(payload["causality_id"], "v2-trace-1")


def _stub_pipeline_deps(**overrides):
    from kernel.pipeline import PipelineDeps

    defaults = dict(
        observe=lambda *a, **k: {},
        cognize=lambda *a, **k: {},
        decide=lambda *a, **k: {"intent": "converse"},
        speak=lambda *a, **k: {"text": "hello"},
        converse_mode_profile=lambda _mode: {"mode": "fast", "thinking_mode": "precision", "inject_memory": False},
        thinking_params=lambda _mode: {},
        touch_activity=lambda: None,
        resolve_model=lambda _id: None,
        threshold_activated_fragments=lambda **k: [],
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
        speech_text=lambda spk: str(spk.get("text", spk) if isinstance(spk, dict) else spk),
        persist_turn=lambda _package: None,
        fast_converse=True,
    )
    defaults.update(overrides)
    return PipelineDeps(**defaults)


class ConverseGeneratorTests(unittest.TestCase):
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
        cls.state_mod = _load_module(f"{pkg}.state", os.path.join(GATEWAY_DIR, "state.py"), pkg)
        cls.events_mod = _load_module(
            "kernel.converse_events",
            os.path.join(KERNEL_DIR, "converse_events.py"),
            "kernel",
        )
        cls.pipeline_mod = _load_module(
            "kernel.pipeline",
            os.path.join(KERNEL_DIR, "pipeline.py"),
            "kernel",
        )
        cls.converse_mod = _load_module(
            f"{pkg}.services.converse",
            os.path.join(GATEWAY_DIR, "services", "converse.py"),
            f"{pkg}.services",
        )

    def test_stream_yields_error_and_done_on_prepare_failure(self):
        commits = []

        def boom_observe(*args, **kwargs):
            raise RuntimeError("prepare failed")

        deps = _stub_pipeline_deps(
            observe=boom_observe,
            persist_turn=lambda _p: commits.append(True),
        )
        state = self.state_mod.EngineStateManager(
            {"consolidation": {}, "current_iteration": 0, "state": type("S", (), {"emotion": type("E", (), {"val": 0, "arousal": 0, "dominance": 0})()})(), "memory_store": {}, "trace": []}
        )
        pipeline = self.pipeline_mod.CognitivePipeline(state, deps)
        service = self.converse_mod.ConverseService(state, pipeline)
        events = list(service.stream_message("hi"))
        kinds = [e["event"] for e in events]
        self.assertIn(self.events_mod.ConverseEventType.ERROR, kinds)
        self.assertIn(self.events_mod.ConverseEventType.DONE, kinds)
        self.assertEqual(commits, [])

    def test_stream_commits_only_after_success(self):
        commits = []
        import time

        class Emotion:
            val = 0.1
            arousal = 0.2
            dominance = 0.3

        class St:
            emotion = Emotion()

        engine = {
            "consolidation": {},
            "current_iteration": 0,
            "state": St(),
            "memory_store": {},
            "trace": [],
        }
        deps = _stub_pipeline_deps(
            persist_turn=lambda _p: commits.append(True),
        )
        state = self.state_mod.EngineStateManager(engine)
        pipeline = self.pipeline_mod.CognitivePipeline(state, deps)
        service = self.converse_mod.ConverseService(state, pipeline)
        events = list(service.stream_message("hi"))
        time.sleep(0.05)
        self.assertEqual(commits, [True])
        self.assertEqual(events[-1]["event"], self.events_mod.ConverseEventType.DONE)


if __name__ == "__main__":
    unittest.main()
