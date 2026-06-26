"""Tests for P5.1 connect observability hook — suggested, not executed."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol.models import Manifest  # noqa: E402
from storage.chunk_store import ChunkStore  # noqa: E402
from storage.descriptor_store import DescriptorStore  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.repair.source_suggestions import suggest_repair_sources  # noqa: E402
from storage.repair_service import RepairService  # noqa: E402
from storage.service import StorageService  # noqa: E402


class SourceSuggestionTests(unittest.TestCase):
    def test_connected_peer_ranked_first(self):
        reg = MagicMock()
        reg.get_all_peers.return_value = {
            "bb" * 32: {"host": "http://other:7864", "status": "trusted"},
        }
        rows = suggest_repair_sources(
            connected_host="http://127.0.0.1:7864",
            connected_peer_id="aa" * 32,
            peer_registry=reg,
        )
        self.assertEqual(rows[0]["rank"], 1)
        self.assertEqual(rows[0]["reason"], "connected_peer")
        self.assertTrue(any(r["reason"] == "trusted_registry_peer" for r in rows))


class ConnectHookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.storage = StorageService(
            ChunkStore(os.path.join(base, "chunks")),
            ManifestStore(os.path.join(base, "manifests.json")),
            DescriptorStore(os.path.join(base, "desc.json")),
        )
        self.repair = RepairService(self.storage)

    def tearDown(self):
        self._tmp.cleanup()

    def test_hook_returns_missing_and_plans_without_execute(self):
        manifest = Manifest.from_chunk_hashes(("aa" * 32,))
        self.storage.manifests.save(manifest)
        hook = self.repair.build_connect_hook(
            peer_host="http://127.0.0.1:7864",
            peer_id="cc" * 32,
        )
        self.assertTrue(hook["ok"])
        self.assertTrue(hook["suggested_only"])
        self.assertFalse(hook["executed"])
        self.assertEqual(hook["missing_count"], 1)
        self.assertEqual(hook["plan_count"], 1)
        self.assertEqual(hook["suggested_sources"][0]["host"], "http://127.0.0.1:7864")
        self.assertNotIn("results", hook)
        self.assertNotIn("repaired", hook)
        self.assertIn("execution_gate", hook)
        self.assertIn("next_steps", hook)


if __name__ == "__main__":
    unittest.main()
