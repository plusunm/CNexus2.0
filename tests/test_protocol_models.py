"""Tests for P0 protocol object model and handshake guard."""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol import (  # noqa: E402
    CNEXUS_PROTOCOL_VERSION,
    DEFAULT_PERSONAL_CAPABILITY,
    CatalogEntry,
    Chunk,
    Commit,
    Graph,
    GraphMetadata,
    HandshakeHello,
    Peer,
    assert_handshake_clean,
    compute_commit_id,
    find_handshake_violations,
    graph_id_for_owner_topic,
    new_graph_id,
)
from protocol.application import CognitiveApplication  # noqa: E402
from protocol.serialization import to_bytes  # noqa: E402


OWNER = "aa" * 32
OTHER = "bb" * 32
CONSTITUTION = "cc" * 32


class ProtocolModelTests(unittest.TestCase):
    def test_graph_id_permanent_across_commits(self):
        graph_id = graph_id_for_owner_topic(OWNER, "Transformer")
        root_a = "11" * 32
        root_b = "22" * 32

        commit_a = Commit.build(
            graph_id=graph_id,
            parent_ids=(),
            root_hash=root_a,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig-a",
        )
        commit_b = Commit.build(
            graph_id=graph_id,
            parent_ids=(commit_a.commit_id,),
            root_hash=root_b,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig-b",
        )

        self.assertEqual(commit_a.graph_id, graph_id)
        self.assertEqual(commit_b.graph_id, graph_id)
        self.assertNotEqual(commit_a.commit_id, commit_b.commit_id)
        self.assertEqual(commit_b.parent_ids, (commit_a.commit_id,))

    def test_owner_topic_namespace_isolation(self):
        g1 = graph_id_for_owner_topic(OWNER, "Transformer")
        g2 = graph_id_for_owner_topic(OTHER, "Transformer")
        self.assertNotEqual(g1, g2)

    def test_merge_commit_dag_two_parents(self):
        graph_id = new_graph_id()
        root = "33" * 32
        a = Commit.build(
            graph_id=graph_id,
            parent_ids=(),
            root_hash=root,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig-root",
        )
        b = Commit.build(
            graph_id=graph_id,
            parent_ids=(a.commit_id,),
            root_hash="44" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig-b",
        )
        c = Commit.build(
            graph_id=graph_id,
            parent_ids=(a.commit_id,),
            root_hash="55" * 32,
            author=OTHER,
            constitution_hash=CONSTITUTION,
            signature="sig-c",
        )
        merge = Commit.build(
            graph_id=graph_id,
            parent_ids=(b.commit_id, c.commit_id),
            root_hash="66" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig-merge",
            message="merge b and c",
        )
        self.assertEqual(len(merge.parent_ids), 2)
        self.assertIn(b.commit_id, merge.parent_ids)
        self.assertIn(c.commit_id, merge.parent_ids)

    def test_serialization_roundtrip_stable_bytes(self):
        graph = Graph(
            graph_id=new_graph_id(),
            owner=OWNER,
            metadata=GraphMetadata(topic="Transformer", constitution_hash=CONSTITUTION),
        )
        raw_a = graph.to_bytes()
        raw_b = Graph.from_bytes(raw_a).to_bytes()
        self.assertEqual(raw_a, raw_b)

    def test_catalog_entry_carries_bloom_not_graph_hashes(self):
        gid = new_graph_id()
        commit = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash="77" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
        )
        entry = CatalogEntry(
            graph_id=gid,
            latest_commit_id=commit.commit_id,
            root_hash=commit.root_hash,
            size=2859312,
            bloom_filter=b"\x01\x02" * 1024,
            owner=OWNER,
            topic="Transformer",
        )
        restored = CatalogEntry.from_dict(entry.to_dict())
        self.assertEqual(restored.bloom_filter, entry.bloom_filter)
        self.assertEqual(restored.topic, "Transformer")

    def test_handshake_forbids_cognitive_fields(self):
        violations = find_handshake_violations(
            {"action": "HELLO", "peer_id": OWNER, "graph_id": new_graph_id()}
        )
        self.assertIn("graph_id", violations)
        with self.assertRaises(ValueError):
            assert_handshake_clean({"audit": {"entries": []}})

    def test_handshake_hello_allowed_fields(self):
        hello = HandshakeHello(
            peer_id=OWNER,
            protocol_version=CNEXUS_PROTOCOL_VERSION,
            capability=DEFAULT_PERSONAL_CAPABILITY,
        )
        assert_handshake_clean(hello.to_dict())

    def test_peer_and_chunk_models(self):
        peer = Peer.from_dict(
            {
                "peer_id": OWNER,
                "capability": DEFAULT_PERSONAL_CAPABILITY,
                "protocol_version": CNEXUS_PROTOCOL_VERSION,
            }
        )
        self.assertEqual(peer.peer_id, OWNER)

        chunk = Chunk.from_content(b"flash-attention", graph_id=new_graph_id())
        self.assertEqual(chunk.length, len(b"flash-attention"))
        self.assertEqual(Chunk.from_bytes(chunk.to_bytes()).chunk_hash, chunk.chunk_hash)

    def test_application_facade_no_network(self):
        class _Mem:
            def __init__(self):
                self.graphs = {}
                self.commits = {}

            def get_graph(self, graph_id):
                return self.graphs.get(graph_id)

            def get_commit(self, commit_id):
                return self.commits.get(commit_id)

            def save_graph(self, graph):
                self.graphs[graph.graph_id] = graph

            def save_commit(self, commit):
                self.commits[commit.commit_id] = commit

        app = CognitiveApplication(store=_Mem())
        gid = new_graph_id()
        graph = Graph(graph_id=gid, owner=OWNER, metadata=GraphMetadata(topic="T"))
        commit = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash="88" * 32,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
        )
        result = app.publish(graph, commit)
        self.assertTrue(result["ok"])
        self.assertEqual(app.sync(gid)["error"], "network_unconfigured")


if __name__ == "__main__":
    unittest.main()
