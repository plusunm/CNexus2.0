"""Tests for control route handler."""

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

    def load(name, relpath, package):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = package
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    load(f"{pkg}.http.responses", os.path.join("http", "responses.py"), f"{pkg}.http")
    load(
        f"{pkg}.services.status_snapshot",
        os.path.join("services", "status_snapshot.py"),
        f"{pkg}.services",
    )
    load(f"{pkg}.services.converse", os.path.join("services", "converse.py"), f"{pkg}.services")
    load(f"{pkg}.services.ingest", os.path.join("services", "ingest.py"), f"{pkg}.services")
    load(
        f"{pkg}.services.gateway_intent",
        os.path.join("services", "gateway_intent.py"),
        f"{pkg}.services",
    )
    load(
        f"{pkg}.services.shadow_projection",
        os.path.join("services", "shadow_projection.py"),
        f"{pkg}.services",
    )
    load(f"{pkg}.services.conflict_control", os.path.join("services", "conflict_control.py"), f"{pkg}.services")
    load(f"{pkg}.services.pruning_control", os.path.join("services", "pruning_control.py"), f"{pkg}.services")
    load(f"{pkg}.services.consensus_control", os.path.join("services", "consensus_control.py"), f"{pkg}.services")
    load(f"{pkg}.services.memory_control", os.path.join("services", "memory_control.py"), f"{pkg}.services")
    load(f"{pkg}.services.replay_control", os.path.join("services", "replay_control.py"), f"{pkg}.services")
    load(f"{pkg}.services.reflection_control", os.path.join("services", "reflection_control.py"), f"{pkg}.services")
    load(f"{pkg}.services.rem_control", os.path.join("services", "rem_control.py"), f"{pkg}.services")
    load(
        f"{pkg}.services.control_plane",
        os.path.join("services", "control_plane.py"),
        f"{pkg}.services",
    )
    return load(f"{pkg}.routes.control", os.path.join("routes", "control.py"), f"{pkg}.routes")


class _FakeHttp:
    def __init__(self, data=None, body=b"{}"):
        self.headers = {"Content-Length": str(len(body))}
        self._data = data or {}
        self.rfile = type("R", (), {"read": lambda _self, n: body[:n]})()

    def _get_post_data(self):
        return dict(self._data)


class _SnapshotStub:
    def build(self):
        return {"status": "online", "schema_version": "2.0"}


class _ShadowStub:
    def cse_synthesize(self, window=200):
        return {"window": window}

    def ollama_start(self):
        return {"started": True}

    def ollama_stop(self):
        return {"stopped": True}


class _IntentConverseStub:
    def run_blocking(self, text, **kwargs):
        return {"reply": f"intent:{text}"}


class _IntentIngestStub:
    def process_staged(self, file_id, policy):
        return {"file_id": file_id, "processed": True}


class _MemoryStub:
    def clear(self, *, keep_models=True):
        return {"cleared": True, "keep_models": keep_models}


class _ReplayStub:
    def run(self, data):
        return {"replay": bool(data.get("force"))}


class _ReflectionStub:
    def reflect_meta(self, data):
        return {"meta": bool(data)}


class _RemStub:
    def run(self, data):
        return {"rem": bool(data.get("force"))}


class _ConflictStub:
    def resolve(self, data):
        return {"resolved": True}, 200

    def update_settings(self, data):
        return {"settings": data}, 200


class _PruningStub:
    def run(self, data):
        return {"pruned": True}, 200


class _ConsensusStub:
    def update_reputation(self, data):
        return {"rep": 1}, 200


class ControlRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control_mod = _load_modules()

    def _handler(self):
        control_plane_mod = sys.modules["cnexus_gateway.services.control_plane"]
        intent_mod = sys.modules["cnexus_gateway.services.gateway_intent"]
        control = control_plane_mod.ControlPlaneService(
            _ShadowStub(),
            _MemoryStub(),
            _ReplayStub(),
            _ReflectionStub(),
            _RemStub(),
            _ConflictStub(),
            _PruningStub(),
            _ConsensusStub(),
        )
        gateway_intent = intent_mod.GatewayIntentService(_IntentConverseStub(), _IntentIngestStub())
        return self.control_mod.ControlRouteHandler(
            control,
            _SnapshotStub(),
            gateway_intent,
        )

    def test_memory_clear(self):
        http = _FakeHttp(body=b'{"keep_models": false}')
        resp = self._handler().handle_post("/api/memory/clear", http)
        self.assertFalse(resp.json_body["keep_models"])

    def test_replay_run(self):
        resp = self._handler().handle_post("/api/replay/run", _FakeHttp({"force": True}))
        self.assertTrue(resp.json_body["replay"])

    def test_v1_post_fallback(self):
        resp = self._handler().handle_post("/v1/system/compute", _FakeHttp())
        self.assertEqual(resp.json_body["schema_version"], "2.0")

    def test_gateway_intent(self):
        resp = self._handler().handle_post(
            "/v1/gateway/intent",
            _FakeHttp({"type": "chat_prepare", "payload": {"text": "hello"}}),
        )
        self.assertTrue(resp.json_body["ok"])
        self.assertEqual(resp.json_body["result"]["user_message"], "hello")

    def test_unhandled_returns_none(self):
        self.assertIsNone(self._handler().handle_post("/api/converse", _FakeHttp()))


if __name__ == "__main__":
    unittest.main()
