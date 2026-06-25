"""Tests for PUT dispatch helper."""

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

    responses = importlib.util.spec_from_file_location(
        f"{pkg}.http.responses",
        os.path.join(GATEWAY_DIR, "http", "responses.py"),
    )
    responses_mod = importlib.util.module_from_spec(responses)
    responses_mod.__package__ = f"{pkg}.http"
    sys.modules[f"{pkg}.http.responses"] = responses_mod
    assert responses.loader is not None
    responses.loader.exec_module(responses_mod)

    dispatch = importlib.util.spec_from_file_location(
        f"{pkg}.http.put_dispatch",
        os.path.join(GATEWAY_DIR, "http", "put_dispatch.py"),
    )
    dispatch_mod = importlib.util.module_from_spec(dispatch)
    dispatch_mod.__package__ = f"{pkg}.http"
    sys.modules[f"{pkg}.http.put_dispatch"] = dispatch_mod
    assert dispatch.loader is not None
    dispatch.loader.exec_module(dispatch_mod)
    return dispatch_mod, responses_mod


class PutDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatch_mod, cls.responses_mod = _load_modules()

    def test_dispatch_first_matching_route(self):
        class _Route:
            def handle_put_route(self, path, http):
                if path == "/models/x":
                    return self.responses_mod.HttpRouteResponse.json({"ok": True})

        route = _Route()
        route.responses_mod = self.responses_mod
        handler = type("H", (), {"_json_calls": [], "_json": lambda s, b, st=200: s._json_calls.append((b, st))})()
        ok = self.dispatch_mod.dispatch_put(handler, "/models/x", [route])
        self.assertTrue(ok)
        self.assertEqual(handler._json_calls[0][0], {"ok": True})

    def test_dispatch_returns_false_when_unhandled(self):
        handler = type("H", (), {})()
        self.assertFalse(self.dispatch_mod.dispatch_put(handler, "/unknown", []))


if __name__ == "__main__":
    unittest.main()
