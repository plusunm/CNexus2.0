"""Tests for P2.1 Catalog Layer — generation, interest, cursors, dynamic bloom."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from catalog.bloom_builder import compute_bloom_params, DEFAULT_TARGET_FPR  # noqa: E402
from catalog.interest import CatalogInterest, filter_entries_by_interest  # noqa: E402
from catalog.service import CatalogService  # noqa: E402
from catalog.store import CatalogStore  # noqa: E402
from protocol import graph_id_for_owner_topic  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class CatalogP21Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = CatalogStore(os.path.join(self._tmp.name, "catalog.json"))
        self.service = CatalogService(self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, topic: str = "AI"):
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
        return self.service.register_graph(graph, commit, chunk_hashes=["ff" * 32], size=100)

    def test_generation_increments_on_register(self):
        self.assertEqual(self.store.generation, 0)
        entry = self._register()
        self.assertEqual(self.store.generation, 1)
        self.assertEqual(entry.head_generation, 1)
        entry2 = self._register()
        self.assertEqual(self.store.generation, 2)
        self.assertEqual(entry2.head_generation, 2)

    def test_head_endpoint_shape(self):
        entry = self._register("Bee")
        payload, status = self.service.get_head(entry.graph_id)
        self.assertEqual(status, 200)
        head = payload["head"]
        self.assertEqual(head["head_commit"], entry.latest_commit_id)
        self.assertEqual(head["head_generation"], entry.head_generation)
        self.assertIn("generation", head)

    def test_interest_filter_topics(self):
        a = self._register("AI")
        b = self._register("Bee")
        rows = self.store.list_entries(interest=CatalogInterest(topics=("AI",)), limit=50)
        ids = {r.graph_id for r in rows}
        self.assertIn(a.graph_id, ids)
        self.assertNotIn(b.graph_id, ids)

    def test_since_commit_cursor_skips_known_head(self):
        entry = self._register()
        rows = self.store.list_entries(
            since_commit_cursors={entry.graph_id: entry.latest_commit_id},
            limit=50,
        )
        self.assertEqual(rows, [])

    def test_bloom_summary_digest_stable(self):
        self._register()
        s1 = self.store.bloom_summary()
        s2 = self.store.bloom_summary()
        self.assertEqual(s1.digest, s2.digest)
        self.assertEqual(s1.generation, self.store.generation)

    def test_dynamic_bloom_params_target_fpr(self):
        m, k = compute_bloom_params(5000, target_fpr=DEFAULT_TARGET_FPR)
        self.assertGreater(m, 4096)
        self.assertGreater(k, 0)

    def test_peer_generation_skip_state(self):
        self._register()
        self.store.set_peer_state(OWNER, generation=self.store.generation, summary_digest="abc")
        state = self.store.get_peer_state(OWNER)
        self.assertEqual(state["generation"], self.store.generation)


if __name__ == "__main__":
    unittest.main()
