"""Tests for peer route handler."""

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
    load(f"{pkg}.http.auth_gate", os.path.join("http", "auth_gate.py"), f"{pkg}.http")
    load(f"{pkg}.services.peer_mesh", os.path.join("services", "peer_mesh.py"), f"{pkg}.services")
    return load(f"{pkg}.routes.peer", os.path.join("routes", "peer.py"), f"{pkg}.routes")


class _FakeHeaders(dict):
    pass


class _FakeHttp:
    def __init__(self, data=None, headers=None):
        self.headers = headers or _FakeHeaders()
        self._data = data or {}

    def _get_post_data(self):
        return dict(self._data)


class _MeshStub:
    def __init__(self, *, deny=False):
        self._deny = deny

    def check_auth(self, path, headers, context, method="GET"):
        if self._deny:
            return {"error": "denied"}, 403
        return None

    def peer_audit(self, since_hash, headers, limit=0):
        return {"since_hash": since_hash, "limit": limit}, 200

    def peer_audit_proof(self, headers):
        return {"proof": True}, 200

    def peer_force_sync(self, data):
        return {"forced": bool(data.get("force"))}, 200

    def peer_sync(self, data, headers):
        return {"sync": True}, 200

    def peer_negotiate(self, data, headers):
        return {"negotiate": True}, 200

    def p2p_handshake(self, data):
        return {"handshake": True}, 200

    def dht_rpc(self, data):
        return {"dht": data.get("op")}, 200

    def connectivity_connect(self, peer_id, hint_host=""):
        return {"peer_id": peer_id, "hint_host": hint_host}, 200

    def catalog_bloom_get(self, namespace="catalog/system"):
        return {"ok": True, "bloom": "AA==", "generation": 1}, 200

    def catalog_generation_get(self):
        return {"ok": True, "generation": 1}, 200

    def catalog_bloom_summary_get(self, namespace="catalog/system"):
        return {"ok": True, "summary": {"digest": "abc"}}, 200

    def catalog_index_get(self, commit_cursors=None, namespace="catalog/system", limit=256, interest=None):
        return {"ok": True, "entries": [], "generation": 1}, 200

    def catalog_status(self):
        return {"ok": True, "catalog": {"graph_count": 0}}, 200

    def cognitive_head_get(self, graph_id):
        return {"ok": True, "head": {"graph_id": graph_id}}, 200

    def cognitive_status(self):
        return {"ok": True, "cognitive": {"graph_count": 0}}, 200

    def network_firewall_ban(self, data):
        return {"banned": data.get("pubkey")}, 200


class _AuthStub:
    def check(self, path, headers, body=None, method="GET"):
        return None


class PeerRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.peer_mod = _load_modules()

    def _handler(self, *, deny=False):
        auth = (
            type("A", (), {"check": lambda *a, **k: ({"error": "denied"}, 403)})()
            if deny
            else _AuthStub()
        )
        return self.peer_mod.PeerRouteHandler(_MeshStub(), auth)

    def test_peer_audit_get(self):
        resp = self._handler().handle_get("/api/peer/audit", "since_hash=abc&limit=10", _FakeHeaders())
        self.assertEqual(resp.json_body["since_hash"], "abc")
        self.assertEqual(resp.json_body["limit"], 10)

    def test_peer_audit_auth_denied(self):
        resp = self._handler(deny=True).handle_get("/api/peer/audit", "", _FakeHeaders())
        self.assertEqual(resp.status, 403)

    def test_connectivity_connect_post(self):
        http = _FakeHttp({"peer_id": "peer-1", "host": "http://127.0.0.1:7864"})
        resp = self._handler().handle_post("/api/connectivity/connect", http)
        self.assertEqual(resp.json_body["peer_id"], "peer-1")
        self.assertEqual(resp.json_body["hint_host"], "http://127.0.0.1:7864")

    def test_catalog_bloom_get(self):
        resp = self._handler().handle_get("/api/catalog/bloom", "", _FakeHeaders())
        self.assertTrue(resp.json_body["ok"])

    def test_catalog_index_get(self):
        resp = self._handler().handle_get("/api/catalog/index", "limit=10", _FakeHeaders())
        self.assertTrue(resp.json_body["ok"])
        self.assertEqual(resp.json_body["generation"], 1)

    def test_catalog_generation_get(self):
        resp = self._handler().handle_get("/api/catalog/generation", "", _FakeHeaders())
        self.assertTrue(resp.json_body["ok"])

    def test_cognitive_head_get(self):
        resp = self._handler().handle_get("/api/cognitive/head", "graph_id=abc", _FakeHeaders())
        self.assertTrue(resp.json_body["ok"])
        self.assertEqual(resp.json_body["head"]["graph_id"], "abc")

    def test_unhandled_returns_none(self):
        self.assertIsNone(self._handler().handle_get("/api/status", "", _FakeHeaders()))
        self.assertIsNone(self._handler().handle_post("/api/converse", _FakeHttp()))


if __name__ == "__main__":
    unittest.main()
