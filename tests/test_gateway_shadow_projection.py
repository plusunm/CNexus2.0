"""Tests for shadow projection service."""

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

    state_path = os.path.join(GATEWAY_DIR, "state.py")
    state_spec = importlib.util.spec_from_file_location(f"{pkg}.state", state_path)
    state_mod = importlib.util.module_from_spec(state_spec)
    state_mod.__package__ = pkg
    sys.modules[f"{pkg}.state"] = state_mod
    assert state_spec.loader is not None
    state_spec.loader.exec_module(state_mod)

    snapshot_path = os.path.join(GATEWAY_DIR, "services", "status_snapshot.py")
    snapshot_spec = importlib.util.spec_from_file_location(f"{pkg}.services.status_snapshot", snapshot_path)
    snapshot_mod = importlib.util.module_from_spec(snapshot_spec)
    snapshot_mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.status_snapshot"] = snapshot_mod
    assert snapshot_spec.loader is not None
    snapshot_spec.loader.exec_module(snapshot_mod)

    shadow_path = os.path.join(GATEWAY_DIR, "services", "shadow_projection.py")
    shadow_spec = importlib.util.spec_from_file_location(f"{pkg}.services.shadow_projection", shadow_path)
    shadow_mod = importlib.util.module_from_spec(shadow_spec)
    shadow_mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.shadow_projection"] = shadow_mod
    assert shadow_spec.loader is not None
    shadow_spec.loader.exec_module(shadow_mod)
    return state_mod, shadow_mod


class _Emotion:
    val = 0.1
    arousal = 0.2
    dominance = 0.3


class _State:
    emotion = _Emotion()
    goal = {"current": "learn", "progress": 0.5}
    meta = {}
    relationship = {}


class _SnapshotStub:
    def build(self):
        return {"emotion": {"valence": 0.1}, "goal": {"current": "learn"}}


class ShadowProjectionServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.shadow_mod = _load_modules()

    def _service(self):
        engine = {
            "state": _State(),
            "memory_store": type("MS", (), {"blocks": []})(),
            "current_iteration": 2,
            "trace": [
                {
                    "trace_id": "t-1",
                    "input": "hello",
                    "speech": {"text": "hi"},
                    "decision": {"intent": "converse"},
                    "iteration": 1,
                }
            ],
            "token_traces": [{"trace_id": "t-1", "tokens_in": 3, "tokens_out": 4, "total": 7}],
            "gtbs_events": [
                {"payload": {"provenance": {"trace_id": "t-1"}}},
            ],
            "runtime_logs": [{"msg": "boot"}],
            "model_registry": {"local": {"provider": "builtin"}},
        }
        return self.shadow_mod.ShadowProjectionService(
            self.state_mod.EngineStateManager(engine),
            _SnapshotStub(),
            self.shadow_mod.ShadowProjectionHooks(
                find_ollama_binary=lambda: None,
                probe_ollama=lambda: False,
                ollama_host="http://127.0.0.1:11434",
                active_chat_model_id=lambda: "local",
            ),
        )

    def test_cse_live(self):
        payload = self._service().cse_live(100)
        self.assertEqual(payload["window_size"], 100)
        self.assertTrue(payload["exec_traces"])

    def test_kernel_record(self):
        record = self._service().kernel_record("t-1")
        self.assertIsNotNone(record)
        self.assertEqual(record["trace_id"], "t-1")
        self.assertEqual(record["events"][0]["payload"]["provenance"]["trace_id"], "t-1")

    def test_api_logs(self):
        payload = self._service().api_logs(10)
        self.assertEqual(payload["count"], 1)


if __name__ == "__main__":
    unittest.main()
