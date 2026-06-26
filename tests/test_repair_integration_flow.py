"""End-to-end dual-node repair flow: hook → gate → confirm → execute."""

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
from protocol.constants import EXECUTION_GATE_ALLOW, EXECUTION_GATE_REQUIRE_CONFIRM  # noqa: E402
from protocol.models import Manifest  # noqa: E402
from storage.chunk_store import ChunkStore  # noqa: E402
from storage.descriptor_store import DescriptorStore  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.repair.execution_policy_store import ExecutionPolicyStore  # noqa: E402
from storage.repair_service import RepairService  # noqa: E402
from storage.service import StorageService  # noqa: E402

OWNER = "aa" * 32


class DualNodeRepairFlowTests(unittest.TestCase):
    """Simulates Node A (local, missing chunks) pulling from Node B (remote, has chunks)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.policy_path = os.path.join(base, "execution_policy.json")
        self.node_b = StorageService(
            ChunkStore(os.path.join(base, "b_chunks")),
            ManifestStore(os.path.join(base, "b_manifests.json")),
            DescriptorStore(os.path.join(base, "b_desc.json")),
        )
        self.node_a = StorageService(
            ChunkStore(os.path.join(base, "a_chunks")),
            ManifestStore(os.path.join(base, "a_manifests.json")),
            DescriptorStore(os.path.join(base, "a_desc.json")),
        )
        self.content = b"dual-node payload"
        self.chunk_hash = compute_chunk_hash(self.content)
        self.node_b.put_chunk(self.content, expected_hash=self.chunk_hash, created_by=OWNER)
        manifest = Manifest.from_chunk_hashes((self.chunk_hash,))
        self.node_a.manifests.save(manifest)
        self.repair_a = RepairService(
            self.node_a,
            policy_store=ExecutionPolicyStore(self.policy_path),
        )
        self._server = None
        self._thread = None
        self.peer_url = ""

    def tearDown(self):
        if self._server:
            self._server.shutdown()
            self._thread.join(timeout=2)
        self._tmp.cleanup()

    def _start_node_b_server(self):
        remote = self.node_b

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                chunk_hash = (qs.get("hash") or [""])[0]
                if parsed.path == "/api/storage/chunk/state":
                    payload, status = remote.chunk_state(chunk_hash)
                elif parsed.path == "/api/storage/chunk":
                    payload, status = remote.chunk_transfer_get(chunk_hash)
                else:
                    payload, status = {"ok": False}, 404
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.peer_url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def test_full_flow_hook_gate_confirm_execute(self):
        self._start_node_b_server()

        hook = self.repair_a.build_connect_hook(
            peer_host=self.peer_url,
            peer_id=OWNER,
            probe_sources=True,
            include_gate=True,
        )
        self.assertTrue(hook["suggested_only"])
        self.assertFalse(hook["executed"])
        self.assertEqual(hook["missing_count"], 1)
        self.assertIn("execution_gate", hook)
        self.assertEqual(hook["execution_gate"]["gate"], EXECUTION_GATE_REQUIRE_CONFIRM)

        gate, status = self.repair_a.evaluate_gate(
            plans=hook["repair_plans"],
            suggested_sources=hook["suggested_sources"],
            user_confirmed=False,
        )
        self.assertEqual(status, 200)
        self.assertEqual(gate["gate"], EXECUTION_GATE_REQUIRE_CONFIRM)

        gate_ok, _ = self.repair_a.evaluate_gate(
            plans=hook["repair_plans"],
            suggested_sources=hook["suggested_sources"],
            user_confirmed=True,
        )
        self.assertEqual(gate_ok["gate"], EXECUTION_GATE_ALLOW)

        result, exec_status = self.repair_a.execute(
            plans=hook["repair_plans"],
            suggested_sources=hook["suggested_sources"],
            user_confirmed=True,
            verifier_peer_id=OWNER,
        )
        self.assertEqual(exec_status, 200)
        self.assertEqual(result.get("repaired"), 1)
        self.assertTrue(self.node_a.chunks.verify(self.chunk_hash))
        self.assertEqual(self.node_a.chunks.get(self.chunk_hash), self.content)


if __name__ == "__main__":
    unittest.main()
