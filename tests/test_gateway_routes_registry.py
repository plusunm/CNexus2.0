"""Tests for POST/PUT route registry."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
SRC_DIR = os.path.join(ROOT, "src")


def _load_registry():
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    for relpath, name in (
        ("http/responses.py", f"{pkg}.http.responses"),
        ("http/post_dispatch.py", f"{pkg}.http.post_dispatch"),
        ("routes/registry.py", f"{pkg}.routes.registry"),
    ):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)

    return sys.modules[f"{pkg}.routes.registry"]


class RoutesRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry_mod = _load_registry()
        cls.responses_mod = sys.modules["cnexus_gateway.http.responses"]

    def _stub_handlers(self):
        HttpRouteResponse = self.responses_mod.HttpRouteResponse

        class Handler:
            def __init__(self, label):
                self.label = label

            def handle_post(self, path, http):
                return HttpRouteResponse.json({"route": self.label, "path": path})

            def handle_http_post(self, path, body, query):
                return HttpRouteResponse.json({"route": self.label, "path": path})

        converse = Handler("converse")
        asset = Handler("asset")
        peer = Handler("peer")
        ingest = Handler("ingest")
        control = Handler("control")
        models = Handler("models")
        return converse, asset, peer, ingest, control, models

    def test_post_routes_order_and_dispatch(self):
        converse, asset, peer, ingest, control, models = self._stub_handlers()
        routes = self.registry_mod.build_post_routes(converse, asset, peer, ingest, control, models)
        self.assertEqual(len(routes), 6)

        http = type("H", (), {"_read_json": lambda s: {}})()
        resp = routes[0](http, "/api/converse", None)
        self.assertEqual(resp.json_body["route"], "converse")

        resp = routes[5](http, "/api/models", None)
        self.assertEqual(resp.json_body["route"], "models")

    def test_put_routes_returns_models_handler(self):
        models = type("Models", (), {})()
        put_routes = self.registry_mod.build_put_routes(models)
        self.assertEqual(tuple(put_routes), (models,))


if __name__ == "__main__":
    unittest.main()
