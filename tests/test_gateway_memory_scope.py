"""Memory scope helpers and recall filtering."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
GATEWAY_DIR = os.path.join(SRC, "gateway")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load(name, relpath, package):
    path = os.path.join(GATEWAY_DIR, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class MemoryScopeTests(unittest.TestCase):
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
        cls.scope_mod = _load(f"{pkg}.services.memory.scope", os.path.join("services", "memory", "scope.py"), f"{pkg}.services.memory")
        cls.state_mod = _load(f"{pkg}.state", os.path.join("state.py"), pkg)
        cls.types_mod = _load(f"{pkg}.services.memory.types", os.path.join("services", "memory", "types.py"), f"{pkg}.services.memory")
        cls.prov_mod = _load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"), f"{pkg}.services.memory")
        cls.context_mod = _load(f"{pkg}.services.memory.context", os.path.join("services", "memory", "context.py"), f"{pkg}.services.memory")
        cls.query_mod = _load(f"{pkg}.services.memory.query", os.path.join("services", "memory", "query.py"), f"{pkg}.services.memory")

    def test_normalize_aliases(self):
        normalize = self.scope_mod.normalize_memory_scope
        self.assertEqual(normalize("group"), "trusted")
        self.assertEqual(normalize("global"), "network")
        self.assertEqual(normalize("unknown"), "local")

    def test_origin_matches_scope(self):
        match = self.scope_mod.origin_matches_scope
        trusted = {"peer-a"}
        self.assertTrue(match("", "local", trusted))
        self.assertFalse(match("peer-a", "local", trusted))
        self.assertTrue(match("peer-a", "trusted", trusted))
        self.assertFalse(match("peer-b", "trusted", trusted))
        self.assertTrue(match("peer-b", "network", trusted))

    def test_recall_respects_trusted_scope(self):
        class _Store:
            blocks = [
                {"block_id": "local-1", "data": {"content": "alpha local note", "source_peer": ""}},
                {"block_id": "peer-1", "data": {"content": "alpha peer note", "source_peer": "peer-a"}},
            ]

        engine = {"memory_store": _Store(), "trace": []}
        state = self.state_mod.EngineStateManager(engine)
        hooks = self.types_mod.MemoryRecallHooks(get_cognitive_pruning_engine=lambda: None)
        provenance = self.prov_mod.DefaultProvenancePort()
        context = self.context_mod.MemoryContextService(provenance)
        svc = self.query_mod.MemoryQueryService(state, hooks, context=context)
        local = svc.recall("alpha", filters=self.types_mod.QueryFilters(scope="local"))
        trusted = svc.recall("alpha", filters=self.types_mod.QueryFilters(scope="trusted", trusted_peers=frozenset({"peer-a"})))
        self.assertIn("alpha local note", local["context"])
        self.assertNotIn("alpha peer note", local["context"])
        self.assertIn("alpha peer note", trusted["context"])


if __name__ == "__main__":
    unittest.main()
