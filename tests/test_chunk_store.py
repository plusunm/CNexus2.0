"""Tests for P4.0 ChunkStore — independent chunk verification."""

import base64
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
from protocol import compute_chunk_hash, graph_id_for_owner_topic  # noqa: E402
from protocol.models import Commit, Graph, GraphMetadata, Manifest  # noqa: E402
from storage.chunk_store import ChunkStore  # noqa: E402
from storage.chunk_verifier import ChunkImmutableError, ChunkVerifyError  # noqa: E402
from storage.descriptor_store import DescriptorStore  # noqa: E402
from storage.manifest_store import ManifestStore  # noqa: E402
from storage.service import StorageService  # noqa: E402

OWNER = "aa" * 32
CONSTITUTION = "cc" * 32


class ChunkStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ChunkStore(os.path.join(self._tmp.name, "chunks"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_put_verify_content_addressed(self):
        content = b"hello chunk truth"
        chunk_hash = self.store.put(content)
        self.assertEqual(chunk_hash, compute_chunk_hash(content))
        self.assertTrue(self.store.verify(chunk_hash))
        self.assertEqual(self.store.get(chunk_hash), content)

    def test_put_rejects_hash_mismatch(self):
        content = b"truth from bytes"
        with self.assertRaises(ChunkVerifyError):
            self.store.put(content, expected_hash="11" * 32)

    def test_rejects_wrong_bytes_for_declared_hash(self):
        content = b"immutable blob"
        chunk_hash = self.store.put(content)
        self.store.put(content)
        with self.assertRaises(ChunkVerifyError):
            self.store.put(b"different bytes", expected_hash=chunk_hash)

    def test_detects_corrupt_local_blob(self):
        content = b"stored truth"
        chunk_hash = self.store.put(content)
        path = self.store._path_for(chunk_hash)
        path.write_bytes(b"tampered")
        self.assertFalse(self.store.verify(chunk_hash))

    def test_dedup_same_content(self):
        content = b"dedup me"
        h1 = self.store.put(content)
        h2 = self.store.put(content)
        self.assertEqual(h1, h2)


class ManifestBindingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.chunk_store = ChunkStore(os.path.join(base, "chunks"))
        self.manifest_store = ManifestStore(os.path.join(base, "manifests.json"))
        self.descriptor_store = DescriptorStore(os.path.join(base, "descriptors.json"))
        self.storage = StorageService(self.chunk_store, self.manifest_store, self.descriptor_store)

    def tearDown(self):
        self._tmp.cleanup()

    def test_manifest_binding_verifies_bytes_not_manifest(self):
        c1 = self.chunk_store.put(b"part-one")
        c2 = self.chunk_store.put(b"part-two")
        manifest = Manifest.from_chunk_hashes((c1, c2))
        self.manifest_store.save(manifest)

        report, status = self.storage.verify_manifest_binding(root_hash=manifest.root_hash)
        self.assertEqual(status, 200)
        self.assertTrue(report["binding_complete"])
        self.assertEqual(report["missing"], [])

    def test_missing_chunks_reported_without_manifest_truth(self):
        manifest = Manifest.from_chunk_hashes(("aa" * 32, "bb" * 32))
        self.manifest_store.save(manifest)
        report, status = self.storage.verify_manifest_binding(root_hash=manifest.root_hash)
        self.assertEqual(status, 200)
        self.assertFalse(report["binding_complete"])
        self.assertEqual(len(report["missing"]), 2)


class PublishWithChunksTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.chunk_store = ChunkStore(os.path.join(base, "chunks"))
        self.manifest_store = ManifestStore(os.path.join(base, "manifests.json"))
        self.descriptor_store = DescriptorStore(os.path.join(base, "descriptors.json"))
        self.storage = StorageService(self.chunk_store, self.manifest_store, self.descriptor_store)
        self.catalog = CatalogService(CatalogStore(os.path.join(base, "catalog.json")))
        self.cognitive = CognitiveService(
            CommitStore(os.path.join(base, "cognitive.json")),
            catalog_service=self.catalog,
            manifest_store=self.manifest_store,
            chunk_store=self.chunk_store,
            storage_service=self.storage,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_publish_stores_chunks_before_manifest(self):
        content_a, content_b = b"alpha", b"beta"
        ha, hb = compute_chunk_hash(content_a), compute_chunk_hash(content_b)
        gid = graph_id_for_owner_topic(OWNER, "ChunkGraph")
        graph = Graph(
            graph_id=gid,
            owner=OWNER,
            metadata=GraphMetadata(topic="ChunkGraph", constitution_hash=CONSTITUTION),
        )
        manifest = Manifest.from_chunk_hashes((ha, hb), graph_id=gid)
        commit = Commit.build(
            graph_id=gid,
            parent_ids=(),
            root_hash=manifest.root_hash,
            author=OWNER,
            constitution_hash=CONSTITUTION,
            signature="sig",
        )
        result = self.cognitive.publish(
            graph,
            commit,
            manifest=manifest,
            chunk_payloads=[
                {"hash": ha, "bytes": base64.b64encode(content_a).decode("ascii")},
                {"hash": hb, "bytes": base64.b64encode(content_b).decode("ascii")},
            ],
            size=len(content_a) + len(content_b),
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["chunk_binding"]["binding_complete"])
        self.assertTrue(self.chunk_store.verify(ha))
        self.assertTrue(self.chunk_store.verify(hb))


if __name__ == "__main__":
    unittest.main()
