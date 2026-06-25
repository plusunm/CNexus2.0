"""Tests for static SPA route handler."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
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
    return load(f"{pkg}.routes.static", os.path.join("routes", "static.py"), f"{pkg}.routes")


class StaticRouteHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static_mod = _load_modules()

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.ui_dir = self._tmpdir.name
        self.handler = self.static_mod.StaticRouteHandler(self.ui_dir)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, relpath: str, content: bytes, *, mode="wb"):
        full = os.path.join(self.ui_dir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, mode) as f:
            f.write(content)

    def test_root_serves_index_html(self):
        self._write("index.html", b"<html>home</html>")
        resp = self.handler.handle_get("/")
        self.assertEqual(resp.mode, "bytes")
        self.assertEqual(resp.bytes_body, b"<html>home</html>")

    def test_existing_asset_file(self):
        self._write("app.js", b"console.log(1)")
        resp = self.handler.handle_get("/app.js")
        self.assertEqual(resp.bytes_body, b"console.log(1)")
        self.assertIn("javascript", resp.content_type)

    def test_missing_asset_returns_404_json(self):
        resp = self.handler.handle_get("/missing.js")
        self.assertEqual(resp.status, 404)
        self.assertIn("Asset not found", resp.json_body["error"])

    def test_spa_fallback_for_page_route(self):
        self._write("index.html", b"<html>spa</html>")
        resp = self.handler.handle_get("/dashboard")
        self.assertEqual(resp.bytes_body, b"<html>spa</html>")

    def test_next_chunk_hash_fallback(self):
        chunk_dir = os.path.join(self.ui_dir, "_next", "static", "chunks")
        os.makedirs(chunk_dir, exist_ok=True)
        with open(os.path.join(chunk_dir, "278.abc123.js"), "wb") as f:
            f.write(b"chunk")
        resp = self.handler.handle_get("/_next/static/chunks/278.js")
        self.assertEqual(resp.bytes_body, b"chunk")

    def test_missing_index_returns_500(self):
        resp = self.handler.handle_get("/dashboard")
        self.assertEqual(resp.status, 500)
        self.assertEqual(resp.json_body["error"], "index.html missing")


if __name__ == "__main__":
    unittest.main()
