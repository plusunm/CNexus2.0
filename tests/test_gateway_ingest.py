"""Unit tests for extracted gateway ingest service."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
KERNEL_DIR = os.path.join(ROOT, "src", "kernel")


def _load_module(name: str, relpath: str, package: str):
    path = os.path.join(GATEWAY_DIR, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_block_store():
    src_dir = os.path.join(ROOT, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    spec = importlib.util.spec_from_file_location(
        "store_reducer",
        os.path.join(KERNEL_DIR, "store_reducer.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.BlockStore()


class DocumentIngestServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pkg = "cnexus_gateway"
        if pkg not in sys.modules:
            init = os.path.join(GATEWAY_DIR, "__init__.py")
            spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
            module = importlib.util.module_from_spec(spec)
            sys.modules[pkg] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
        cls.state_mod = _load_module(f"{pkg}.state", "state.py", pkg)
        cls.ingest_mod = _load_module(f"{pkg}.services.ingest", os.path.join("services", "ingest.py"), f"{pkg}.services")

    def setUp(self):
        self.persist_calls = 0
        self.logs: list[str] = []
        self.tmp = tempfile.mkdtemp()
        self.engine = {
            "memory_store": _load_block_store(),
            "gtbs_events": [],
            "runtime_logs": [],
            "consolidation": {},
        }
        self.state = self.state_mod.EngineStateManager(self.engine)
        hooks = self.ingest_mod.IngestHooks(
            touch_activity=lambda: None,
            append_log=lambda msg, **kwargs: self.logs.append(msg),
            gtbs_row=lambda *args, **kwargs: {"event_type": args[0], "payload": kwargs},
            schedule_persist=lambda: setattr(self, "persist_calls", self.persist_calls + 1),
        )
        self.service = self.ingest_mod.DocumentIngestService(self.state, hooks, assets_dir=self.tmp)

    def test_stage_and_process_indexes_memory(self):
        payload, status = self.service.stage_upload("notes.txt", b"hello CNexus ingest")
        self.assertEqual(status, 200)
        file_id = payload["file_id"]
        result = self.service.process_staged(file_id, {"layer": "episodic", "importance": 0.8})
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(len(self.engine["memory_store"].blocks), 2)
        self.assertEqual(self.persist_calls, 1)

    def test_ingest_document_one_shot(self):
        payload, status = self.service.ingest_document("doc.md", b"# Title\nBody text", layer="goal")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(os.listdir(self.tmp))
        self.assertGreaterEqual(len(self.engine["memory_store"].blocks), 1)

    def test_stage_documents_batch_fast_receive(self):
        files = [("a.txt", b"alpha"), ("b.txt", b"beta")]
        payload, status = self.service.stage_documents_batch(files)
        self.assertEqual(status, 200)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["file_ids"]), 2)
        self.assertFalse(os.listdir(self.tmp))

    def test_process_staged_batch_indexes_once(self):
        staged, _ = self.service.stage_documents_batch(
            [("a.txt", b"alpha one"), ("b.txt", b"beta two")],
        )
        result = self.service.process_staged_batch(staged["file_ids"], {"layer": "episodic"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(self.engine["memory_store"].blocks), 2)
        self.assertEqual(self.persist_calls, 1)

    def test_ingest_documents_batch(self):
        files = [
            ("a.txt", b"alpha document one"),
            ("b.txt", b"beta document two"),
            ("c.txt", b"gamma document three"),
        ]
        payload, status = self.service.ingest_documents_batch(files, layer="episodic")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 3)
        self.assertEqual(len(payload["indexed"]), 3)
        self.assertEqual(len(self.engine["memory_store"].blocks), 3)
        self.assertEqual(self.persist_calls, 1)
        self.assertEqual(len(self.logs), 1)

    def test_capture_text(self):
        result = self.service.capture_text("direct capture", label="note")
        self.assertTrue(result["ok"])
        self.assertEqual(self.persist_calls, 1)

    def test_process_staged_batch_streaming_reports_progress_and_prioritizes_text(self):
        staged, _ = self.service.stage_documents_batch(
            [("heavy.pdf", b"pdf"), ("fast.md", b"# fast"), ("slow.docx", b"doc")],
        )
        progress: list[dict] = []

        def on_progress(**fields):
            progress.append(dict(fields))

        result = self.service.process_staged_batch_streaming(
            staged["file_ids"],
            {"layer": "episodic"},
            on_progress,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 3)
        self.assertGreaterEqual(len(progress), 2)
        self.assertEqual(progress[-1]["done"], 3)
        first_detail = progress[1]["details"][0]["filename"]
        self.assertTrue(first_detail.endswith(".md"))


if __name__ == "__main__":
    unittest.main()
