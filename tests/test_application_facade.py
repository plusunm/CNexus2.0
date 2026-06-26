"""Application Facade — unified semantic entry over cognitive / catalog / storage / repair."""

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

from application.facade import ApplicationFacade  # noqa: E402
from application.state import PHASE_DIAGNOSED, PHASE_GATE_PREVIEW, PHASE_PUBLISHED  # noqa: E402
from catalog.service import CatalogService  # noqa: E402
from catalog.store import CatalogStore  # noqa: E402
from cognitive.commit_store import CommitStore  # noqa: E402
from cognitive.service import CognitiveService  # noqa: E402
from protocol import compute_chunk_hash, graph_id_for_owner_topic  # noqa: E402
from protocol.constants import EXECUTION_GATE_REQUIRE_CONFIRM  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata, Manifest  # noqa: E402
from storage.chunk_store import ChunkStore  # noqa: E402
from storage.descriptor_store import DescriptorStore  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.repair.execution_policy_store import ExecutionPolicyStore  # noqa: E402
from storage.repair_service import RepairService  # noqa: E402
from storage.service import StorageService  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class ApplicationFacadeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.commit_store = CommitStore(os.path.join(base, "cognitive.json"))
        self.catalog = CatalogService(CatalogStore(os.path.join(base, "catalog.json")))
        self.manifest_store = ManifestStore(os.path.join(base, "manifests.json"))
        self.storage = StorageService(
            ChunkStore(os.path.join(base, "chunks")),
            self.manifest_store,
            DescriptorStore(os.path.join(base, "descriptors.json")),
        )
        self.cognitive = CognitiveService(
            self.commit_store,
            catalog_service=self.catalog,
            manifest_store=self.manifest_store,
            storage_service=self.storage,
        )
        self.repair = RepairService(
            self.storage,
            catalog_service=self.catalog,
            policy_store=ExecutionPolicyStore(os.path.join(base, "policy.json")),
        )
        self.memory_blocks = [
            {"block_id": "b1", "label": "note", "content": "hello facade"},
            {"block_id": "b2", "label": "note", "content": "world facade"},
        ]
        self.app = ApplicationFacade(
            cognitive=self.cognitive,
            catalog=self.catalog,
            storage=self.storage,
            repair_service=self.repair,
            memory_blocks=lambda: self.memory_blocks,
            identity_pubkey=lambda: OWNER,
            constitution_hash=CONSTITUTION,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_status_exposes_control_surface(self):
        status = self.app.status()
        self.assertTrue(status["ok"])
        self.assertEqual(status["layer"], "application")
        self.assertEqual(status["memory_block_count"], 2)
        self.assertIn("control", status)

    def test_publish_memory_wires_memory_to_catalog(self):
        result = self.app.publish_memory(topic="memory/test")
        self.assertTrue(result["ok"])
        self.assertEqual(self.app.control.phase, PHASE_PUBLISHED)
        gid = result["graph_id"]
        found = self.app.find(graph_id=gid)
        self.assertEqual(found["count"], 1)
        self.assertTrue(self.storage.chunks.verify(result["manifest"]["chunks"][0]))

    def test_diagnose_local_without_peer(self):
        content = b"orphan manifest chunk"
        chunk_hash = compute_chunk_hash(content)
        manifest = Manifest.from_chunk_hashes((chunk_hash,))
        self.manifest_store.save(manifest)
        report = self.app.diagnose(scope="all")
        self.assertTrue(report["ok"])
        self.assertEqual(self.app.control.phase, PHASE_DIAGNOSED)
        self.assertGreater(report["plan_count"], 0)

    def test_absorb_connect_updates_phase(self):
        hook = {
            "ok": True,
            "missing_count": 1,
            "plan_count": 1,
            "execution_gate": {"gate": EXECUTION_GATE_REQUIRE_CONFIRM},
        }
        view = self.app.absorb_connect(
            {
                "ok": True,
                "url": "http://127.0.0.1:7864",
                "peer_id": OWNER,
                "repair_hook": hook,
            }
        )
        self.assertEqual(view["phase"], PHASE_GATE_PREVIEW)
        self.assertIn("next_steps", view)

    def test_repair_flow_hook_gate_execute(self):
        content = b"remote chunk for facade"
        chunk_hash = compute_chunk_hash(content)
        manifest = Manifest.from_chunk_hashes((chunk_hash,))
        self.manifest_store.save(manifest)

        remote = StorageService(
            ChunkStore(os.path.join(self._tmp.name, "remote_chunks")),
            ManifestStore(os.path.join(self._tmp.name, "remote_manifests.json")),
            DescriptorStore(os.path.join(self._tmp.name, "remote_desc.json")),
        )
        remote.put_chunk(content, expected_hash=chunk_hash, created_by=OWNER)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                h = (qs.get("hash") or [""])[0]
                if parsed.path.endswith("/chunk/state"):
                    payload, status = remote.chunk_state(h)
                elif parsed.path.endswith("/chunk"):
                    payload, status = remote.chunk_transfer_get(h)
                else:
                    payload, status = {"ok": False}, 404
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(("127.0.0.1", 0), Handler)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            hook, status = self.app.repair("hook", peer_host=url, peer_id=OWNER)
            self.assertEqual(status, 200)
            self.assertEqual(hook["action"], "hook")

            gate, gate_status = self.app.repair(
                "gate",
                plans=hook["repair_plans"],
                suggested_sources=hook["suggested_sources"],
                confirm=False,
            )
            self.assertEqual(gate_status, 200)
            self.assertEqual(gate["gate"], EXECUTION_GATE_REQUIRE_CONFIRM)

            denied, deny_status = self.app.repair(
                "execute",
                plans=hook["repair_plans"],
                suggested_sources=hook["suggested_sources"],
                confirm=False,
            )
            self.assertEqual(deny_status, 409)

            result, exec_status = self.app.repair(
                "execute",
                plans=hook["repair_plans"],
                suggested_sources=hook["suggested_sources"],
                confirm=True,
            )
            self.assertEqual(exec_status, 200)
            self.assertEqual(result.get("repaired"), 1)
            self.assertTrue(self.storage.chunks.verify(chunk_hash))
        finally:
            server.shutdown()
            thread.join(timeout=2)

    def test_find_filters_by_topic(self):
        gid = graph_id_for_owner_topic(OWNER, "alpha")
        graph = Graph(graph_id=gid, owner=OWNER, metadata=GraphMetadata(topic="alpha"))
        manifest = Manifest.from_chunk_hashes(())
        commit = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash=manifest.root_hash,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
        )
        self.cognitive.publish(graph, commit, manifest=manifest)
        rows = self.app.find(topic="alpha")
        self.assertEqual(rows["count"], 1)
        empty = self.app.find(topic="missing-topic")
        self.assertEqual(empty["count"], 0)


if __name__ == "__main__":
    unittest.main()
