"""Tests for Memory Domain query service."""

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
    return state_mod, query_mod


class _FakeStore:
    def __init__(self, blocks):
        self.blocks = blocks


class MemoryQueryServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.query_mod = _load_modules()

    def _service(self, engine):
        return self.query_mod.MemoryQueryService(
            self.state_mod.EngineStateManager(engine),
            self.query_mod.MemoryRecallHooks(
                get_cognitive_pruning_engine=lambda: None,
            ),
        )

    def test_search_returns_recall_result(self):
        engine = {
            "memory_store": _FakeStore([{"block_id": "b1", "data": {"content": "asyncio patterns"}}]),
            "trace": [],
        }
        result = self._service(engine).search("asyncio")
        self.assertEqual(len(result.fragments), 1)
        self.assertIn("asyncio", result.fragments[0].snippet)

    def test_search_block_rows_for_asset_merge(self):
        store = _FakeStore([{"block_id": "b1", "data": {"content": "neural memory", "tag": "episode"}}])
        engine = {"memory_store": store, "trace": []}
        rows = self._service(engine).search_block_rows(store, "neural", limit=5)
        self.assertEqual(rows[0]["kind"], "memory")
        self.assertIn("neural", rows[0]["summary"])


if __name__ == "__main__":
    unittest.main()
