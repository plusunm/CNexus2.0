"""Tests for unified auth gate."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_module():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    path = os.path.join(GATEWAY_DIR, "http", "auth_gate.py")
    name = f"{pkg}.http.auth_gate"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.http"
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class AuthGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_check_allows_when_deny_returns_none(self):
        gate = self.mod.AuthGate(lambda *a, **k: None)
        self.assertIsNone(gate.check("/api/asset/x", {}, {"asset_id": "x"}, method="GET"))

    def test_check_blocks_when_deny_returns_error(self):
        gate = self.mod.AuthGate(lambda *a, **k: ({"error": "denied"}, 403))
        err, status = gate.check("/api/asset/x", {}, {}, method="GET")
        self.assertEqual(status, 403)

    def test_allow_preserves_multipart_body_stream(self):
        boundary = "----cnexus"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="files"; filename="t.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "hello\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        consumed: list[int] = []

        class _Handler:
            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            }

            class _RFile:
                def __init__(self, payload: bytes):
                    self._payload = payload
                    self._pos = 0

                def read(self, n: int = -1) -> bytes:
                    if n < 0:
                        n = len(self._payload) - self._pos
                    chunk = self._payload[self._pos : self._pos + n]
                    consumed.append(len(chunk))
                    self._pos += len(chunk)
                    return chunk

            def __init__(self):
                self.rfile = self._RFile(body)

            def _get_post_data(self):
                raise AssertionError("multipart auth must not parse JSON body")

            def _json(self, data, status=200):
                raise AssertionError(f"unexpected deny: {data} ({status})")

        handler = _Handler()
        gate = self.mod.AuthGate(lambda *a, **k: None)
        self.assertTrue(gate.allow(handler, "/api/ingest/documents/stage"))
        self.assertEqual(sum(consumed), 0)
        self.assertEqual(handler.rfile.read(), body)


if __name__ == "__main__":
    unittest.main()
