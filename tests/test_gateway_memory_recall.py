"""Tests for memory recall service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_modules():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    def load(name, relpath):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = name.rsplit(".", 1)[0] if "." in name else pkg
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_mod = load(f"{pkg}.state", "state.py")
    load(f"{pkg}.services.memory.types", os.path.join("services", "memory", "types.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.context", os.path.join("services", "memory", "context.py"))
    load(f"{pkg}.services.memory.query", os.path.join("services", "memory", "query.py"))
    recall_mod = load(f"{pkg}.services.memory_recall", os.path.join("services", "memory_recall.py"))
    return state_mod, recall_mod


class _FakeStore:
    def __init__(self, blocks):
        self.blocks = blocks


class _FakePrune:
    def __init__(self, active_ids):
        self._active = set(active_ids)

    def block_is_active(self, block):
        return block.get("block_id") in self._active


class _FakeProv:
    PROVENANCE_AUDIT_PREVIEW = "audit-preview"

    @staticmethod
    def from_block(block):
        return "local-full"

    @staticmethod
    def format_fragment(snippet, *, provenance, source_peer="", block_id=""):
        return f"[{provenance}|{block_id}|{source_peer}] {snippet}"

    @staticmethod
    def is_preview(provenance):
        return provenance == "audit-preview"

    @staticmethod
    def preview_tag(provenance):
        return ""

    @staticmethod
    def build_preamble():
        return ""


class MemoryRecallServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.recall_mod = _load_modules()

    def _service(self, engine, *, prune_active=None, pull_assets=False):
        class Prov(_FakeProv):
            pass

        prune_ids = prune_active if prune_active is not None else ["b1", "b2"]

        class _Assets:
            pulled = []

            def blob_present(self, asset_id):
                return False

            def peer_pull_enabled(self):
                return pull_assets

            def ensure_local_for_recall(self, asset_id, *, source_peer):
                self.pulled.append((asset_id, source_peer))
                return {"ok": True}

        assets = _Assets() if pull_assets else None
        service = self.recall_mod.MemoryRecallService(
            self.state_mod.EngineStateManager(engine),
            self.recall_mod.MemoryRecallHooks(
                get_cognitive_pruning_engine=lambda: _FakePrune(prune_ids),
            ),
            provenance=Prov(),
            assets=assets,
            max_hits=5,
        )
        return service, assets

    def test_recall_matches_block_content(self):
        engine = {
            "memory_store": _FakeStore(
                [
                    {"block_id": "b1", "data": {"content": "Python asyncio patterns"}},
                    {"block_id": "b2", "data": {"content": "unrelated topic"}},
                ]
            ),
            "trace": [],
        }
        result = self._service(engine)[0].recall("asyncio")
        self.assertIn("asyncio", result["context"])
        self.assertNotIn("unrelated", result["context"])

    def test_recall_falls_back_to_trace(self):
        engine = {
            "memory_store": _FakeStore([]),
            "trace": [
                {"input": "earlier unrelated", "trace_id": "t0"},
                {"input": "discussed neural memory recall", "trace_id": "t1", "replayed": True},
            ],
        }
        result = self._service(engine)[0].recall("neural")
        self.assertIn("neural memory recall", result["context"])
        self.assertIn("audit-preview", result["context"])

    def test_recall_empty_query_returns_all_active_blocks(self):
        engine = {
            "memory_store": _FakeStore(
                [
                    {"block_id": "b1", "data": {"content": "first"}},
                    {"block_id": "b2", "data": {"content": "second"}},
                ]
            ),
            "trace": [],
        }
        result = self._service(engine)[0].recall("")
        self.assertIn("first", result["context"])
        self.assertIn("second", result["context"])

    def test_recall_respects_pruning(self):
        engine = {
            "memory_store": _FakeStore(
                [
                    {"block_id": "b1", "data": {"content": "active block"}},
                    {"block_id": "b2", "data": {"content": "pruned block"}},
                ]
            ),
            "trace": [],
        }
        result = self._service(engine, prune_active=["b1"])[0].recall("")
        self.assertIn("active block", result["context"])
        self.assertNotIn("pruned block", result["context"])

    def test_recall_no_hits_message(self):
        engine = {"memory_store": _FakeStore([]), "trace": []}
        result = self._service(engine)[0].recall("missing")
        self.assertIn("未检索到", result["context"])
        self.assertIn("missing", result["context"])


    def test_recall_pulls_missing_asset_blob(self):
        engine = {
            "memory_store": _FakeStore(
                [{"block_id": "b1", "data": {"content": "asset doc", "asset_id": "a1", "source_peer": "peer1"}}]
            ),
            "trace": [],
        }
        service, assets = self._service(engine, pull_assets=True)
        service.recall("asset")
        self.assertEqual(assets.pulled, [("a1", "peer1")])


if __name__ == "__main__":
    unittest.main()
