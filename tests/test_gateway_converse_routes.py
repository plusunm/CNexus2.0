"""Tests for converse route handler."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
GATEWAY_DIR = os.path.join(SRC, "gateway")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


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
    load(f"{pkg}.services.converse", os.path.join("services", "converse.py"), f"{pkg}.services")
    load(f"{pkg}.services.converse_config", os.path.join("services", "converse_config.py"), f"{pkg}.services")
    return load(f"{pkg}.routes.converse", os.path.join("routes", "converse.py"), f"{pkg}.routes")


class _FakeService:
    def __init__(self, result=None, error=None):
        self._result = result or {"reply": "hello", "trace_id": "t1"}
        self._error = error
        self.last_call = None

    def run_blocking(self, input_text, *, model_id=None, converse_mode="fast", thinking_mode="precision", memory_scope="local"):
        self.last_call = {
            "input_text": input_text,
            "model_id": model_id,
            "converse_mode": converse_mode,
            "thinking_mode": thinking_mode,
            "memory_scope": memory_scope,
        }
        if self._error:
            raise self._error
        return dict(self._result)


class _FakeHttp:
    def __init__(self, data=None, headers=None):
        self.headers = headers or {}
        self._data = data or {}

    def _get_post_data(self):
        return dict(self._data)


class _ConfigStub:
    def parse_request_modes(self, data):
        payload = data or {}
        return (
            str(payload.get("converse_mode") or "fast"),
            str(payload.get("thinking_mode") or "precision"),
        )

    def parse_memory_scope(self, data):
        payload = data or {}
        return str(payload.get("memory_scope") or "local")


class ConverseRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.converse_mod = _load_modules()

    def _handler(self, service=None, *, stream_default=False):
        return self.converse_mod.ConverseRouteHandler(
            service or _FakeService(),
            _ConfigStub(),
            stream_default=stream_default,
        )

    def test_converse_get_with_text(self):
        service = _FakeService({"reply": "world", "trace_id": "abc"})
        resp = self._handler(service).handle_get("/api/converse", "text=hi&converse_mode=deep&thinking_mode=emergent&memory_scope=trusted")
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.json_body["ok"])
        self.assertEqual(resp.json_body["reply"], "world")
        self.assertEqual(service.last_call["input_text"], "hi")
        self.assertEqual(service.last_call["converse_mode"], "deep")
        self.assertEqual(service.last_call["thinking_mode"], "emergent")
        self.assertEqual(service.last_call["memory_scope"], "trusted")

    def test_converse_get_without_text_returns_none(self):
        self.assertIsNone(self._handler().handle_get("/api/converse", ""))

    def test_converse_get_service_error_returns_500(self):
        resp = self._handler(_FakeService(error=RuntimeError("boom"))).handle_get(
            "/api/converse", "text=fail"
        )
        self.assertEqual(resp.status, 500)
        self.assertFalse(resp.json_body["ok"])

    def test_unhandled_path_returns_none(self):
        self.assertIsNone(self._handler().handle_get("/api/status", "text=hi"))

    def test_converse_post_json(self):
        resp = self._handler().handle_post("/api/converse", _FakeHttp({"text": "hi"}))
        self.assertEqual(resp.mode, "json")
        self.assertEqual(resp.json_body["reply"], "hello")

    def test_converse_post_missing_text_400(self):
        resp = self._handler().handle_post("/api/converse", _FakeHttp({}))
        self.assertEqual(resp.status, 400)

    def test_converse_stream_post_sse(self):
        class _StreamSvc(_FakeService):
            def stream_message(self, *args, **kwargs):
                yield {"event": "token", "data": "x"}

        resp = self._handler(_StreamSvc()).handle_post(
            "/api/converse/stream",
            _FakeHttp({"text": "stream me"}),
        )
        self.assertEqual(resp.mode, "sse")
        self.assertIsNotNone(resp.sse_body)

    def test_post_unhandled_returns_none(self):
        self.assertIsNone(self._handler().handle_post("/api/status", _FakeHttp()))


if __name__ == "__main__":
    unittest.main()
