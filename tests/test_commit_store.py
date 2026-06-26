"""Tests for CommitStore persistence."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cognitive.commit_store import CommitStore  # noqa, E402
from protocol import graph_id_for_owner_topic  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class CommitStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = CommitStore(os.path.join(self._tmp.name, "cognitive.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def _graph(self, topic: str = "TestGraph") -> Graph:
        gid = graph_id_for_owner_topic(OWNER, topic)
        return Graph(
            graph_id=gid,
            owner=OWNER,
            metadata=GraphMetadata(topic=topic, constitution_hash=CONSTITUTION),
        )

    def _commit(self, graph: Graph, *, parent_ids=(), root="11" * 32, ts=1.0) -> Commit:
        return Commit.build(
            graph_id=graph.graph_id,
            parent_ids=parent_ids,
            root_hash=root,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
            timestamp=ts,
        )

    def test_save_and_reload(self):
        graph = self._graph()
        commit = self._commit(graph)
        self.store.save_graph(graph)
        self.store.save_commit(commit)

        restored = CommitStore(os.path.join(self._tmp.name, "cognitive.json"))
        self.assertEqual(restored.get_head_commit_id(graph.graph_id), commit.commit_id)
        self.assertIsNotNone(restored.get_graph(graph.graph_id))
        self.assertIsNotNone(restored.get_commit(commit.commit_id))

    def test_save_commits_chain(self):
        graph = self._graph()
        c1 = self._commit(graph, ts=1.0)
        c2 = self._commit(graph, parent_ids=(c1.commit_id,), root="22" * 32, ts=2.0)
        self.store.save_graph(graph)
        self.store.save_commits([c1, c2])
        self.assertEqual(self.store.get_head_commit_id(graph.graph_id), c2.commit_id)


if __name__ == "__main__":
    unittest.main()
