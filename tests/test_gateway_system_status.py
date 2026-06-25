"""Tests for system status route handler."""

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

    state_mod = load(f"{pkg}.state", "state.py", pkg)
    probe_mod = load(f"{pkg}.services.system_probe", os.path.join("services", "system_probe.py"), f"{pkg}.services")
    load(f"{pkg}.http.responses", os.path.join("http", "responses.py"), f"{pkg}.http")
    subsystems_mod = load(
        f"{pkg}.services.status_subsystems",
        os.path.join("services", "status_subsystems.py"),
        f"{pkg}.services",
    )
    snapshot_mod = load(
        f"{pkg}.services.status_snapshot",
        os.path.join("services", "status_snapshot.py"),
        f"{pkg}.services",
    )
    dashboard_mod = load(
        f"{pkg}.services.dashboard_status",
        os.path.join("services", "dashboard_status.py"),
        f"{pkg}.services",
    )
    peers_mod = load(
        f"{pkg}.services.peers_status",
        os.path.join("services", "peers_status.py"),
        f"{pkg}.services",
    )
    shadow_mod = load(
        f"{pkg}.services.shadow_projection",
        os.path.join("services", "shadow_projection.py"),
        f"{pkg}.services",
    )
    recall_mod = load(
        f"{pkg}.services.memory_recall",
        os.path.join("services", "memory_recall.py"),
        f"{pkg}.services",
    )
    routes_mod = load(f"{pkg}.routes.system_status", os.path.join("routes", "system_status.py"), f"{pkg}.routes")
    return state_mod, probe_mod, subsystems_mod, snapshot_mod, dashboard_mod, peers_mod, shadow_mod, recall_mod, routes_mod


class _Emotion:
    val = 0.0
    arousal = 0.0
    dominance = 0.0


class _State:
    emotion = _Emotion()
    goal = {"current": "explore", "progress": 0.0}
    meta = {}
    relationship = {}


class _SubsystemsStub:
    def replay_status(self):
        return {"enabled": True}

    def awakening_status(self):
        return {"phase": "idle"}

    def reflection_status(self):
        return {"enabled": True}

    def conflict_resolution_status(self):
        return {"enabled": True}

    def negotiation_conflict_recent(self):
        return {"items": []}

    def pruning_status(self):
        return {"enabled": False}

    def entropy_status(self):
        return {"local": "0x1"}


class _SnapshotStub:
    def build(self):
        return {"schema_version": "2.0", "status": "online", "emotion": {}, "goal": {}}


class _DashboardStub:
    def build(self):
        return {"ok": True}


class _PeersStub:
    def build(self):
        return {"peers": {}, "peer_count": 0}


class _ShadowStub:
    def cse_live(self, window):
        return {"window": window}

    def execution_status(self):
        return {"running": False}

    def ollama_status(self):
        return {"running": False}

    def api_logs(self, limit):
        return {"logs": [], "limit": limit}

    def gtbs_events(self, limit):
        return {"events": []}

    def token_observatory(self, limit):
        return {"items": []}

    def runtime_introspect(self):
        return {"ok": True}

    def token_field(self, trace_id):
        return {"trace_id": trace_id}

    def kernel_records_recent(self, limit):
        return {"records": []}

    def kernel_learn(self, trace_id):
        return {"trace_id": trace_id}

    def kernel_record(self, trace_id):
        return {"trace_id": trace_id}


class _NetworkStub:
    def build(self):
        return {"connectivity": {"enabled": True}}

    def dht_status(self):
        return {"enabled": True}


class _RecallStub:
    def recall(self, query):
        return {"context": query}


class SystemStatusRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.probe_mod, cls.subsystems_mod, cls.snapshot_mod, cls.dashboard_mod, cls.peers_mod, cls.shadow_mod, cls.recall_mod, cls.routes_mod = _load_modules()

    def _handler(self):
        engine = {"started_at": 1_700_000_000.0, "memory_store": type("S", (), {"blocks": [1, 2, 3]})()}
        probe = self.probe_mod.SystemProbeService(self.state_mod.EngineStateManager(engine))
        return self.routes_mod.SystemStatusRouteHandler(
            probe,
            _SubsystemsStub(),
            _SnapshotStub(),
            _DashboardStub(),
            _PeersStub(),
            _NetworkStub(),
            _ShadowStub(),
            _RecallStub(),
        )

    def test_api_status(self):
        resp = self._handler().handle_get("/api/status", "")
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.json_body["schema_version"], "2.0")

    def test_dashboard_status(self):
        resp = self._handler().handle_get("/api/dashboard/status", "")
        self.assertTrue(resp.json_body["ok"])

    def test_v1_gateway_health(self):
        resp = self._handler().handle_get("/v1/gateway/health", "")
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.json_body["gateway"], "alive")

    def test_memory_stats_from_probe(self):
        resp = self._handler().handle_get("/v1/memory/stats", "")
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.json_body["total"], 3)

    def test_unhandled_path_returns_none(self):
        self.assertIsNone(self._handler().handle_get("/api/asset/list", ""))

    def test_v1_fallback(self):
        resp = self._handler().handle_get("/v1/unknown/route", "")
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)
        self.assertIn("L0 fallback", resp.json_body["message"])

    def test_replay_status_from_subsystems(self):
        resp = self._handler().handle_get("/api/replay/status", "")
        self.assertTrue(resp.json_body["enabled"])

    def test_cse_live_from_shadow(self):
        resp = self._handler().handle_get("/v1/cse/live", "window=50")
        self.assertEqual(resp.json_body["window"], 50)


    def test_connectivity_status(self):
        resp = self._handler().handle_get("/api/connectivity/status", "")
        self.assertTrue(resp.json_body["network"]["connectivity"]["enabled"])

    def test_dht_status(self):
        resp = self._handler().handle_get("/api/dht/status", "")
        self.assertTrue(resp.json_body["dht"]["enabled"])


if __name__ == "__main__":
    unittest.main()
