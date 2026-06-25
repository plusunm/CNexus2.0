"""Tests for ingest route handler."""

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
    return load(f"{pkg}.routes.ingest", os.path.join("routes", "ingest.py"), f"{pkg}.routes")


class _FakeHttp:
    def __init__(self, data=None):
        self.headers = {}
        self.rfile = None
        self._data = data or {}

    def _get_post_data(self):
        return dict(self._data)


class IngestRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ingest_routes_mod = _load_modules()

    def _handler(self):
        class _Svc:
            def capture_text(self, content, *, layer, label, importance):
                return {"ok": True, "content": content, "layer": layer, "label": label, "importance": importance}

            def ingest_document(self, *args, **kwargs):
                return {"ok": True, "ingested": True}, 200

        return self.ingest_routes_mod.IngestRouteHandler(_Svc())

    def test_memory_capture_post(self):
        resp = self._handler().handle_post(
            "/v1/memory/capture",
            _FakeHttp({"content": "note", "layer": "goal", "importance": 0.8}),
        )
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.json_body["content"], "note")
        self.assertEqual(resp.json_body["layer"], "goal")

    def test_unhandled_returns_none(self):
        self.assertIsNone(self._handler().handle_post("/api/converse", _FakeHttp()))


if __name__ == "__main__":
    unittest.main()
