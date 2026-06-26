"""Tests for P4.5 ChunkDescriptor contract and chunk transfer."""

import base64
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
from protocol.models import ChunkDescriptor  # noqa: E402
from storage.chunk_store import ChunkStore  # noqa: E402
from storage.descriptor_store import DescriptorStore  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.service import StorageService  # noqa: E402

OWNER = "aa" * 32


class ChunkDescriptorTests(unittest.TestCase):
    def test_descriptor_wire_format(self):
        content = b"network atom"
        chunk_hash = compute_chunk_hash(content)
        desc = ChunkDescriptor.for_content(content, chunk_hash, created_by=OWNER)
        row = desc.to_dict()
        self.assertEqual(row["hash"], chunk_hash)
        self.assertEqual(row["encoding"], "raw")
        self.assertEqual(row["size"], len(content))
        restored = ChunkDescriptor.from_dict(row)
        self.assertEqual(restored.chunk_hash, chunk_hash)

    def test_descriptor_not_manifest_field(self):
        desc = ChunkDescriptor.for_content(b"x", compute_chunk_hash(b"x"))
        self.assertNotIn("root_hash", desc.to_dict())
        self.assertNotIn("chunks", desc.to_dict())


class ChunkStateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.storage = StorageService(
            ChunkStore(os.path.join(base, "chunks")),
            ManifestStore(os.path.join(base, "manifests.json")),
            DescriptorStore(os.path.join(base, "descriptors.json")),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_chunk_state_without_bytes(self):
        content = b"state probe"
        chunk_hash = compute_chunk_hash(content)
        self.storage.put_chunk(content, expected_hash=chunk_hash, created_by=OWNER)
        state, status = self.storage.chunk_state(chunk_hash)
        self.assertEqual(status, 200)
        self.assertTrue(state["exists"])
        self.assertTrue(state["verified"])
        self.assertEqual(state["encoding"], "raw")
        self.assertNotIn("bytes", state)


class ChunkTransferTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.remote = StorageService(
            ChunkStore(os.path.join(base, "remote_chunks")),
            ManifestStore(os.path.join(base, "remote_manifests.json")),
            DescriptorStore(os.path.join(base, "remote_desc.json")),
        )
        self.local = StorageService(
            ChunkStore(os.path.join(base, "local_chunks")),
            ManifestStore(os.path.join(base, "local_manifests.json")),
            DescriptorStore(os.path.join(base, "local_desc.json")),
        )
        self.content = b"multi-source truth"
        self.chunk_hash = compute_chunk_hash(self.content)
        self.remote.put_chunk(self.content, expected_hash=self.chunk_hash, created_by=OWNER)
        self._server = None
        self._thread = None
        self._port = 0

    def tearDown(self):
        if self._server:
            self._server.shutdown()
            self._thread.join(timeout=2)
        self._tmp.cleanup()

    def _start_server(self, storage: StorageService):
        service = storage

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                chunk_hash = (qs.get("hash") or [""])[0]
                if parsed.path == "/api/storage/chunk/state":
                    payload, status = service.chunk_state(chunk_hash)
                elif parsed.path == "/api/storage/chunk":
                    payload, status = service.chunk_transfer_get(chunk_hash)
                else:
                    payload, status = {"ok": False}, 404
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def test_pull_request_verify_store(self):
        self._start_server(self.remote)
        peer_host = f"http://127.0.0.1:{self._port}"
        report = self.local.pull_chunk_from_peer(peer_host, self.chunk_hash, verifier_peer_id=OWNER)
        self.assertTrue(report.get("ok"))
        self.assertTrue(self.local.chunks.verify(self.chunk_hash))
        self.assertEqual(self.local.chunks.get(self.chunk_hash), self.content)

    def test_rejects_bad_bytes_from_peer(self):
        bad_storage = self.local

        class BadHandler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                chunk_hash = (qs.get("hash") or [""])[0]
                if parsed.path == "/api/storage/chunk/state":
                    payload = {"ok": True, "exists": True, "encoding": "raw"}
                    status = 200
                elif parsed.path == "/api/storage/chunk":
                    payload = {
                        "ok": True,
                        "hash": chunk_hash,
                        "encoding": "raw",
                        "bytes": base64.b64encode(b"poison").decode("ascii"),
                    }
                    status = 200
                else:
                    payload, status = {"ok": False}, 404
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(("127.0.0.1", 0), BadHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            report = bad_storage.pull_chunk_from_peer(
                f"http://127.0.0.1:{port}",
                self.chunk_hash,
                verifier_peer_id=OWNER,
            )
            self.assertFalse(report.get("ok"))
            self.assertEqual(report.get("error"), "verify_failed")
            self.assertFalse(bad_storage.chunks.has(self.chunk_hash))
        finally:
            server.shutdown()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
