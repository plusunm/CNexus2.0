"""Tests for Catalog Layer — Bloom filter, store, and exchange."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from catalog.bloom_filter import BloomFilter  # noqa: E402
from catalog.service import CatalogService  # noqa: E402
from catalog.store import CatalogStore  # noqa: E402
from protocol import graph_id_for_owner_topic, new_graph_id  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class CatalogLayerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = CatalogStore(os.path.join(self._tmp.name, "catalog.json"))
        self.service = CatalogService(self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def _register_sample(self, topic: str = "Transformer"):
        gid = graph_id_for_owner_topic(OWNER, topic)
        graph = Graph(graph_id=gid, owner=OWNER, metadata=GraphMetadata(topic=topic, constitution_hash=CONSTITUTION))
        commit = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash="11" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
        )
        return self.service.register_graph(graph, commit, chunk_hashes=["aa" * 32, "bb" * 32], size=1024)

    def test_bloom_filter_compact(self):
        bloom = BloomFilter()
        for i in range(500):
            bloom.add(f"chunk-{i}")
        encoded = bloom.to_base64()
        self.assertLess(len(encoded), 32 * 1024)
        restored = BloomFilter.from_base64(encoded)
        self.assertTrue(restored.might_contain("chunk-0"))
        self.assertFalse(restored.might_contain("missing-chunk"))

    def test_catalog_entry_persisted(self):
        entry = self._register_sample()
        restored = self.store.get_entry(entry.graph_id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.latest_commit_id, entry.latest_commit_id)
        self.assertEqual(restored.topic, "Transformer")

    def test_index_exchange_merges_newer(self):
        local = self._register_sample("LocalGraph")
        other_gid = new_graph_id()
        remote_entry = {
            "object_type": "catalog_entry",
            "schema_version": 1,
            "graph_id": other_gid,
            "latest_commit_id": "dd" * 32,
            "root_hash": "22" * 32,
            "size": 2048,
            "bloom_filter": BloomFilter().to_base64(),
            "updated_at": 9999999999.0,
            "owner": OWNER,
            "topic": "RemoteGraph",
        }
        result = self.service.exchange_index(remote_entries=[remote_entry])
        self.assertEqual(result["merged"], 1)
        self.assertIsNotNone(self.store.get_entry(other_gid))
        self.assertIsNotNone(self.store.get_entry(local.graph_id))

    def test_bloom_exchange_payload(self):
        self._register_sample()
        payload = self.service.exchange_bloom("")
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["bloom"])


if __name__ == "__main__":
    unittest.main()
