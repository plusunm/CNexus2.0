"""Tests for asset route handler."""

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

    responses_mod = load(f"{pkg}.http.responses", os.path.join("http", "responses.py"), f"{pkg}.http")
    load(f"{pkg}.http.auth_gate", os.path.join("http", "auth_gate.py"), f"{pkg}.http")
    load(f"{pkg}.services.ingest", os.path.join("services", "ingest.py"), f"{pkg}.services")
    load(f"{pkg}.utils.multipart", os.path.join("utils", "multipart.py"), f"{pkg}.utils")
    load(f"{pkg}.services.asset_gateway", os.path.join("services", "asset_gateway.py"), f"{pkg}.services")
    load(f"{pkg}.routes.ingest", os.path.join("routes", "ingest.py"), f"{pkg}.routes")
    asset_mod = load(f"{pkg}.routes.asset", os.path.join("routes", "asset.py"), f"{pkg}.routes")
    return responses_mod, asset_mod


class _FakeHeaders(dict):
    pass


class _FakeHttp:
    def __init__(self, data=None, headers=None, body=b"{}"):
        self.headers = headers or _FakeHeaders({"Content-Length": str(len(body))})
        self._data = data or {}
        self.rfile = type("R", (), {"read": lambda _self, n: body[:n]})()

    def _get_post_data(self):
        return dict(self._data)


class _AssetsStub:
    def __init__(self):
        self.touch_count = 0

    def check_auth(self, *args, **kwargs):
        return None

    def search(self, q, **k):
        return {"q": q, **k}, 200

    def get_processor(self):
        class Proc:
            @staticmethod
            def read_raw(asset_id):
                return b"print('hi')", {"type": "code", "filename": f"{asset_id}.py"}, 200

        return Proc()

    def get_asset(self, asset_id, **k):
        return {"asset_id": asset_id, **k}, 200

    def upload_code(self, data):
        self.touch_count += 1
        return {"uploaded": data}


class _IngestStub:
    def handle_gateway_file_upload(self, rfile, headers):
        return {"file": True}, 200


class _AuthStub:
    def check(self, path, headers, body=None, method="GET"):
        return None


class AssetRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.responses_mod, cls.asset_mod = _load_modules()

    def _handler(self):
        return self.asset_mod.AssetRouteHandler(_AssetsStub(), _IngestStub(), _AuthStub())

    def test_asset_search_get(self):
        resp = self._handler().handle_get("/api/asset/search", "q=hello&limit=5", _FakeHeaders())
        self.assertIsNotNone(resp)
        self.assertEqual(resp.mode, "json")
        self.assertEqual(resp.json_body["q"], "hello")

    def test_asset_raw_bytes(self):
        resp = self._handler().handle_get("/api/asset/abc123", "raw=1", _FakeHeaders())
        self.assertEqual(resp.mode, "bytes")
        self.assertIn(b"print", resp.bytes_body)

    def test_upload_code_post(self):
        assets = _AssetsStub()
        handler = self.asset_mod.AssetRouteHandler(assets, _IngestStub(), _AuthStub())
        http = _FakeHttp({"filename": "a.py"})
        resp = handler.handle_post("/api/upload/code", http)
        self.assertEqual(resp.json_body["uploaded"]["filename"], "a.py")
        self.assertEqual(assets.touch_count, 1)

    def test_unhandled_returns_none(self):
        self.assertIsNone(self._handler().handle_get("/api/status", "", _FakeHeaders()))
        self.assertIsNone(self._handler().handle_post("/api/converse", _FakeHttp()))


if __name__ == "__main__":
    unittest.main()
