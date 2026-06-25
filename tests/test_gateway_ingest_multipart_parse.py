"""Compare ingest parse paths with requests-generated bodies."""
from __future__ import annotations

import importlib.util
import io
import os
import sys
import unittest

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load_ingest_routes():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    path = os.path.join(GATEWAY_DIR, "routes", "ingest.py")
    name = f"{pkg}.routes.ingest"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.routes"
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _Svc:
    def stage_documents_batch(self, files):
        return {"ok": True, "trace_id": "t1", "file_ids": ["f1"], "count": len(files), "status": "received"}, 200

    def stage_upload(self, filename, raw, *, persist_blob=True):
        return {"ok": True, "file_id": "f1", "trace_id": "f1", "filename": filename, "file_type": "txt"}, 200


class _Http:
    def __init__(self, prep):
        body = prep.body if isinstance(prep.body, bytes) else prep.body.encode()
        self.headers = dict(prep.headers)
        self.headers["Content-Length"] = str(len(body))
        self.rfile = io.BytesIO(body)


class IngestParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = _load_ingest_routes()
        cls.handler = cls.routes.IngestRouteHandler(_Svc())

    def test_stage_with_requests_files_field(self):
        prep = requests.Request(
            "POST",
            "http://127.0.0.1/stage",
            files=[("files", ("t.txt", b"hello", "text/plain"))],
        ).prepare()
        resp = self.handler.handle_post("/api/ingest/documents/stage", _Http(prep))
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200, resp.json_body)

    def test_upload_with_requests_file_field(self):
        prep = requests.Request(
            "POST",
            "http://127.0.0.1/upload",
            files={"file": ("t.txt", b"hello", "text/plain")},
        ).prepare()
        payload, status = self.handler.handle_gateway_file_upload(_Http(prep).rfile, _Http(prep).headers)
        self.assertEqual(status, 200, payload)


if __name__ == "__main__":
    unittest.main()
