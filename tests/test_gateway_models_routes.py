"""Tests for models route HTTP adapters."""

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
    return load(f"{pkg}.routes.models", os.path.join("routes", "models.py"), f"{pkg}.routes")


class _FakeService:
    def list_models(self):
        return {"models": []}


class ModelsRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models_mod = _load_modules()

    def _handler(self):
        return self.models_mod.ModelsRouteHandler(_FakeService())

    def test_http_get_models(self):
        resp = self._handler().handle_http_get("/api/models", "")
        self.assertIsNotNone(resp)
        self.assertEqual(resp.mode, "json")

    def test_http_get_unhandled_returns_none(self):
        self.assertIsNone(self._handler().handle_http_get("/api/status", ""))

    def test_handle_put_route(self):
        class _Svc:
            def upsert(self, model_id, body, create=False):
                return {"id": model_id, **body}, None

        handler = self.models_mod.ModelsRouteHandler(_Svc())
        http = type("H", (), {"_read_json": lambda _self: {"name": "m1"}})()
        resp = handler.handle_put_route("/api/models/m1", http)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.json_body["model"]["id"], "m1")


if __name__ == "__main__":
    unittest.main()
