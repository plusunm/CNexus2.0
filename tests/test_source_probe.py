"""Tests for P5.2 source probe enrichment — state only, no pull."""

import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol import compute_chunk_hash  # noqa: E402
from protocol.models import Manifest  # noqa: E402
from storage.chunk_store import ChunkStore  # noqa: E402
from storage.descriptor_store import DescriptorStore  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.repair.source_probe import (  # noqa: E402
    PROBE_CHECK_METHOD,
    PROBE_CONFIDENCE,
    enrich_suggested_sources,
    probe_chunk_state,
)
from storage.repair_service import RepairService  # noqa: E402
from storage.service import StorageService  # noqa: E402


class SourceProbeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.remote = StorageService(
            ChunkStore(os.path.join(base, "remote")),
            ManifestStore(os.path.join(base, "remote_m.json")),
            DescriptorStore(os.path.join(base, "remote_d.json")),
        )
        self.content = b"probe target"
        self.chunk_hash = compute_chunk_hash(self.content)
        self.remote.put_chunk(self.content, expected_hash=self.chunk_hash)
        self._server = None
        self._thread = None
        self._port = 0
        self._get_calls = 0

    def tearDown(self):
        if self._server:
            self._server.shutdown()
            self._thread.join(timeout=2)
        self._tmp.cleanup()

    def _start_state_only_server(self):
        remote = self.remote
        state_calls = {"n": 0, "transfer": 0}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                chunk_hash = (qs.get("hash") or [""])[0]
                if parsed.path == "/api/storage/chunk/state":
                    state_calls["n"] += 1
                    payload, status = remote.chunk_state(chunk_hash)
                elif parsed.path == "/api/storage/chunk":
                    state_calls["transfer"] += 1
                    self.send_response(403)
                    self.end_headers()
                    return
                else:
                    payload, status = {"ok": False}, 404
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._state_calls = state_calls
        return f"http://127.0.0.1:{self._port}"

    def test_probe_uses_state_not_transfer(self):
        peer = self._start_state_only_server()
        state = probe_chunk_state(peer, self.chunk_hash)
        self.assertTrue(state["state_checked"])
        self.assertTrue(state["remote_has"])
        self.assertEqual(state["check_method"], PROBE_CHECK_METHOD)
        self.assertEqual(state["confidence"], PROBE_CONFIDENCE)
        self.assertEqual(self._state_calls["n"], 1)
        self.assertEqual(self._state_calls["transfer"], 0)

    def test_connect_hook_enriched_without_execute(self):
        peer = self._start_state_only_server()
        local = StorageService(
            ChunkStore(os.path.join(self._tmp.name, "local")),
            ManifestStore(os.path.join(self._tmp.name, "local_m.json")),
            DescriptorStore(os.path.join(self._tmp.name, "local_d.json")),
        )
        manifest = Manifest.from_chunk_hashes((self.chunk_hash, "bb" * 32))
        local.manifests.save(manifest)
        repair = RepairService(local)
        hook = repair.build_connect_hook(peer_host=peer, peer_id="aa" * 32, probe_sources=True)
        self.assertTrue(hook["probe_enabled"])
        self.assertFalse(hook["executed"])
        src = hook["suggested_sources"][0]
        self.assertTrue(src["state_checked"])
        self.assertFalse(src["remote_has"])
        self.assertTrue(src["remote_has_partial"])
        self.assertEqual(src["probe"]["remote_has_count"], 1)
        self.assertEqual(src["probe"]["missing_queried"], 2)
        self.assertEqual(src["probe"]["check_method"], "chunk/state")
        self.assertEqual(self._state_calls["transfer"], 0)


if __name__ == "__main__":
    unittest.main()
