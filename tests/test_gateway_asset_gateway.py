"""Tests for AssetGatewayService + MemoryAssetService integration."""

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

    def load(name, relpath, package=None):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = package or name.rsplit(".", 1)[0]
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_mod = load(f"{pkg}.state", "state.py")
    load(f"{pkg}.http.auth_gate", os.path.join("http", "auth_gate.py"), f"{pkg}.http")
    load(f"{pkg}.services.memory.types", os.path.join("services", "memory", "types.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.context", os.path.join("services", "memory", "context.py"))
    query_mod = load(f"{pkg}.services.memory.query", os.path.join("services", "memory", "query.py"))
    asset_mem_mod = load(f"{pkg}.services.memory.asset", os.path.join("services", "memory", "asset.py"))
    gateway_mod = load(f"{pkg}.services.asset_gateway", os.path.join("services", "asset_gateway.py"))
    return state_mod, query_mod, asset_mem_mod, gateway_mod


class _FakeStore:
    def __init__(self, blocks):
        self.blocks = blocks


class AssetGatewayServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.query_mod, cls.asset_mem_mod, cls.gateway_mod = _load_modules()

    def _memory_assets(self, engine):
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

        return self.asset_mem_mod.MemoryAssetService(
            self.state_mod.EngineStateManager(engine),
            query,
            self.asset_mem_mod.MemoryAssetHooks(
                load_federated_search_module=lambda: _Fed(),
                get_peer_registry=lambda: None,
                get_dht_service=lambda: None,
                get_identity_manager=lambda: None,
                build_signed_headers=lambda *a, **k: {},
                blob_present=lambda _id: True,
                peer_pull_enabled=lambda: False,
                ensure_local=lambda *a, **k: {"ok": True},
            ),
        )

    def _gateway(self, engine):
        class Proc:
            @staticmethod
            def search(query, *, kind=None, limit=20):
                return [{"asset_id": "a1", "score": 0.5, "filename": "doc.py"}]

            @staticmethod
            def _read_meta(asset_id):
                return {"source_peer": None, "summary": "code asset"}

        return self.gateway_mod.AssetGatewayService(
            self.gateway_mod.AssetGatewayHooks(
                get_asset_processor=lambda: Proc(),
                get_vector_index=lambda: None,
                get_clip_embedder=lambda: None,
                get_asset_peer_sync=lambda: None,
                get_asset_push_queue=lambda: None,
                after_asset_indexed=lambda *a, **k: None,
                schedule_persist=lambda: None,
                asset_peer_push_enabled=lambda: False,
            ),
            auth=type("Auth", (), {"check": lambda *a, **k: None})(),
            projection=type("Proj", (), {"ingest_code": lambda *a, **k: {}, "ingest_image": lambda *a, **k: {}})(),
            memory_assets=self._memory_assets(engine),
            touch_activity=lambda: None,
        )

    def test_search_merges_memory_rows(self):
        engine = {
            "memory_store": _FakeStore(
                [{"block_id": "b1", "data": {"content": "neural gateway merge", "tag": "episode"}}]
            ),
            "trace": [],
        }
        body, code = self._gateway(engine).search("neural", limit=10)
        self.assertEqual(code, 200)
        kinds = {row.get("kind") for row in body["hits"]}
        self.assertIn("memory", kinds)
        self.assertIn("asset", kinds)


if __name__ == "__main__":
    unittest.main()
