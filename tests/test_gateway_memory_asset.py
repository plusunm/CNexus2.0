"""Tests for MemoryAssetService — unified memory rows + blob port."""

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
        mod.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_mod = load(f"{pkg}.state", "state.py")
    load(f"{pkg}.services.memory.types", os.path.join("services", "memory", "types.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.context", os.path.join("services", "memory", "context.py"))
    query_mod = load(f"{pkg}.services.memory.query", os.path.join("services", "memory", "query.py"))
    asset_mod = load(f"{pkg}.services.memory.asset", os.path.join("services", "memory", "asset.py"))
    return state_mod, query_mod, asset_mod


class _FakeStore:
    def __init__(self, blocks):
        self.blocks = blocks


class MemoryAssetServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.query_mod, cls.asset_mod = _load_modules()

    def _service(self, engine):
        query = self.query_mod.MemoryQueryService(
            self.state_mod.EngineStateManager(engine),
            self.query_mod.MemoryRecallHooks(get_cognitive_pruning_engine=lambda: None),
        )

        class _Fed:
            @staticmethod
            def trusted_peer_pubkeys(_registry):
                return set()

            @staticmethod
            def filter_rows_by_scope(rows, _scope, _trusted):
                return rows

            @staticmethod
            def merge_search_hits(*groups, limit=30):
                merged = []
                for group in groups:
                    merged.extend(group)
                return merged[:limit]

        return self.asset_mod.MemoryAssetService(
            self.state_mod.EngineStateManager(engine),
            query,
            self.asset_mod.MemoryAssetHooks(
                load_federated_search_module=lambda: _Fed(),
                get_peer_registry=lambda: None,
                get_dht_service=lambda: None,
                get_identity_manager=lambda: None,
                build_signed_headers=lambda *a, **k: {},
                blob_present=lambda asset_id: asset_id == "local1",
                peer_pull_enabled=lambda: True,
                ensure_local=lambda asset_id, **k: {"ok": True, "asset_id": asset_id},
            ),
        )

    def test_search_memory_rows_uses_query_service(self):
        engine = {
            "memory_store": _FakeStore(
                [{"block_id": "b1", "data": {"content": "neural memory asset", "tag": "episode"}}]
            ),
            "trace": [],
        }
        rows = self._service(engine).search_memory_rows("neural", limit=5)
        self.assertEqual(rows[0]["kind"], "memory")
        self.assertIn("neural", rows[0]["summary"])

    def test_blob_port_for_recall(self):
        engine = {"memory_store": _FakeStore([]), "trace": []}
        assets = self._service(engine)
        self.assertTrue(assets.blob_present("local1"))
        self.assertFalse(assets.blob_present("missing"))
        report = assets.ensure_local_for_recall("local1", source_peer="peer1")
        self.assertTrue(report.get("ok"))


if __name__ == "__main__":
    unittest.main()
