"""Tests for P5 integrity-driven repair."""

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
from storage.repair.diff_engine import diff_manifest  # noqa: E402
from storage.repair.planner import build_repair_plans  # noqa: E402
from storage.repair_service import RepairService  # noqa: E402
from storage.service import StorageService  # noqa: E402

OWNER = "aa" * 32


class MissingDiffTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.chunks = ChunkStore(os.path.join(base, "chunks"))
        self.manifests = ManifestStore(os.path.join(base, "manifests.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_detect_missing_and_present(self):
        c1 = self.chunks.put(b"have")
        manifest = Manifest.from_chunk_hashes((c1, "bb" * 32))
        self.manifests.save(manifest)
        diff = diff_manifest(manifest, self.chunks)
        self.assertEqual(list(diff.present), [c1])
        self.assertEqual(list(diff.missing), ["bb" * 32])


class RepairPlannerTests(unittest.TestCase):
    def test_plan_only_for_missing(self):
        manifest = Manifest.from_chunk_hashes(("aa" * 32, "bb" * 32))
        diff = diff_manifest(manifest, ChunkStore(tempfile.mkdtemp()))
        plans = build_repair_plans(diff, sources=["http://peer:7864"])
        self.assertEqual(len(plans), 2)
        self.assertGreater(plans[0].priority, 0)
        self.assertEqual(plans[0].strategy, "pull_verify_store")


class RepairExecutorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.storage = StorageService(
            ChunkStore(os.path.join(base, "local")),
            ManifestStore(os.path.join(base, "manifests.json")),
            DescriptorStore(os.path.join(base, "desc.json")),
        )
        self.remote = StorageService(
            ChunkStore(os.path.join(base, "remote")),
            ManifestStore(os.path.join(base, "remote_manifests.json")),
            DescriptorStore(os.path.join(base, "remote_desc.json")),
        )
        self.repair = RepairService(self.storage)
        self.content = b"repair me"
        self.chunk_hash = compute_chunk_hash(self.content)
        self.remote.put_chunk(self.content, expected_hash=self.chunk_hash, created_by=OWNER)
        self._server = None
        self._thread = None

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
                self.end_headers()
                self.wfile.write(body)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://127.0.0.1:{port}"

    def test_repair_flow_diff_plan_execute(self):
        manifest = Manifest.from_chunk_hashes((self.chunk_hash,))
        self.storage.manifests.save(manifest)
        peer = self._start_server(self.remote)

        diff_resp, status = self.repair.detect_missing(root_hash=manifest.root_hash)
        self.assertEqual(status, 200)
        self.assertEqual(diff_resp["diff"]["missing"], [self.chunk_hash])

        plan_resp, status = self.repair.generate_plan(root_hash=manifest.root_hash, sources=[peer])
        self.assertEqual(status, 200)
        self.assertEqual(plan_resp["count"], 1)

        exec_resp, status = self.repair.execute(
            plans=plan_resp["plans"],
            suggested_sources=[
                {
                    "host": peer,
                    "reason": "connected_peer",
                    "probe": {
                        "state_checked": True,
                        "remote_has": True,
                        "chunk_states": [
                            {
                                "hash": self.chunk_hash,
                                "remote_has": True,
                                "state_checked": True,
                            }
                        ],
                    },
                }
            ],
            user_confirmed=True,
            verifier_peer_id=OWNER,
        )
        self.assertEqual(status, 200)
        self.assertEqual(exec_resp["repaired"], 1)
        self.assertTrue(self.storage.chunks.verify(self.chunk_hash))


if __name__ == "__main__":
    unittest.main()
