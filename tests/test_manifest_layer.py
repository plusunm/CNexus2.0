"""Tests for P3.5 Manifest layer and PublishTxn recovery."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from catalog.service import CatalogService  # noqa: E402
from catalog.store import CatalogStore  # noqa: E402
from cognitive.commit_store import CommitStore  # noqa: E402
from cognitive.service import CognitiveService  # noqa: E402
from protocol import compute_root_hash, graph_id_for_owner_topic  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata, Manifest  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.publish_txn import PublishTxnStore  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class ManifestLayerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.commit_store = CommitStore(os.path.join(base, "cognitive.json"))
        self.catalog_store = CatalogStore(os.path.join(base, "catalog.json"))
        self.catalog = CatalogService(self.catalog_store)
        self.manifest_store = ManifestStore(os.path.join(base, "manifests.json"))
        self.txn_store = PublishTxnStore(os.path.join(base, "publish_txn.json"))
        self.service = CognitiveService(
            self.commit_store,
            catalog_service=self.catalog,
            manifest_store=self.manifest_store,
            txn_store=self.txn_store,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _publish_sample(self, chunks=("aa" * 32, "bb" * 32)):
        gid = graph_id_for_owner_topic(OWNER, "ManifestGraph")
        graph = Graph(
            graph_id=gid,
            owner=OWNER,
            metadata=GraphMetadata(topic="ManifestGraph", constitution_hash=CONSTITUTION),
        )
        manifest = Manifest.from_chunk_hashes(chunks, graph_id=gid)
        commit = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash=manifest.root_hash,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
        )
        return graph, commit, manifest

    def test_manifest_root_hash_derivation(self):
        h1, h2 = "11" * 32, "22" * 32
        manifest = Manifest.from_chunk_hashes((h2, h1))
        self.assertEqual(manifest.root_hash, compute_root_hash((h1, h2)))
        self.assertTrue(manifest.verify_root())

    def test_publish_persists_manifest_not_payload(self):
        graph, commit, manifest = self._publish_sample()
        result = self.service.publish(graph, commit, manifest=manifest, size=128)
        self.assertTrue(result["ok"])
        stored = self.manifest_store.get(commit.root_hash)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.chunk_hashes(), manifest.chunk_hashes())
        entry = self.catalog_store.get_entry(graph.graph_id)
        self.assertEqual(entry.root_hash, manifest.root_hash)
        self.assertEqual(list(entry.chunks), list(manifest.chunk_hashes()))

    def test_publish_txn_recovery_after_catalog_drift(self):
        graph, commit, manifest = self._publish_sample()
        self.manifest_store.save(manifest, commit_id=commit.commit_id)
        self.commit_store.save_graph(graph)
        self.commit_store.save_commit(commit)
        txn = self.txn_store.begin(graph, commit, manifest, size=64)
        self.txn_store.advance(txn.txn_id, "pending_catalog")

        healed = self.service.heal_catalog_drift()
        self.assertEqual(healed, 1)
        entry = self.catalog_store.get_entry(graph.graph_id)
        self.assertEqual(entry.latest_commit_id, commit.commit_id)

        self.assertTrue(self.service.replay_txn(txn))
        self.txn_store.complete(txn.txn_id)
        self.assertEqual(self.txn_store.status()["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()
