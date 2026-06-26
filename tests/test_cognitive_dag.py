"""Tests for cognitive DAG utilities and service."""

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
from cognitive.dag import commits_since  # noqa: E402
from cognitive.service import CognitiveService  # noqa: E402
from protocol import compute_root_hash, graph_id_for_owner_topic  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata, Manifest  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class CognitiveDagTests(unittest.TestCase):
    def _chain(self):
        gid = graph_id_for_owner_topic(OWNER, "Chain")
        graph = Graph(graph_id=gid, owner=OWNER, metadata=GraphMetadata(topic="Chain", constitution_hash=CONSTITUTION))
        c1 = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash="11" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
            timestamp=1.0,
        )
        c2 = Commit.build(
            graph_id=gid,
            parent_ids=(c1.commit_id,),
            root_hash="22" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
            timestamp=2.0,
        )
        c3 = Commit.build(
            graph_id=gid,
            parent_ids=(c2.commit_id,),
            root_hash="33" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
            timestamp=3.0,
        )
        store = {c.commit_id: c for c in (c1, c2, c3)}
        return graph, c1, c2, c3, store.get

    def test_commits_since_oldest_first(self):
        graph, c1, c2, c3, get_commit = self._chain()
        rows = commits_since(c3.commit_id, c1.commit_id, get_commit)
        self.assertEqual([r.commit_id for r in rows], [c2.commit_id, c3.commit_id])

    def test_atomic_publish_updates_catalog(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            catalog_store = CatalogStore(os.path.join(tmp.name, "catalog.json"))
            catalog = CatalogService(catalog_store)
            commit_store = CommitStore(os.path.join(tmp.name, "cognitive.json"))
            service = CognitiveService(commit_store, catalog_service=catalog)

            graph, c1, _, _, _ = self._chain()
            manifest = Manifest.from_chunk_hashes(("aa" * 32,), graph_id=graph.graph_id)
            c1 = Commit.build(
                graph_id=graph.graph_id,
                parent_ids=(),
                root_hash=manifest.root_hash,
                author=OWNER,
                constitution_hash=CONSTITUTION,
                signature="sig",
                timestamp=1.0,
            )
            result = service.publish(graph, c1, manifest=manifest, size=512)
            self.assertTrue(result["ok"])
            self.assertEqual(commit_store.get_head_commit_id(graph.graph_id), c1.commit_id)
            entry = catalog_store.get_entry(graph.graph_id)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.latest_commit_id, c1.commit_id)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
