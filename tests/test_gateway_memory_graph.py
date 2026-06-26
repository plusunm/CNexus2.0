"""Tests for MemoryGraphService spread + adjacency."""

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
    load(f"{pkg}.services.converse_speech", os.path.join("services", "converse_speech.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.wormhole_embed", os.path.join("services", "memory", "wormhole_embed.py"))
    graph_mod = load(f"{pkg}.services.memory.graph", os.path.join("services", "memory", "graph.py"))
    return state_mod, graph_mod


class MemoryGraphServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.graph_mod = _load_modules()

    def _service(self, engine):
        return self.graph_mod.MemoryGraphService(
            self.state_mod.EngineStateManager(engine),
            self.graph_mod.MemoryGraphHooks(
                extract_keywords=lambda text, limit: [text[:3]] if text else [],
            ),
            config=self.graph_mod.MemoryGraphConfig(wormhole_max_compare=0, recent_blocks=20),
        )

    def test_build_adjacency_links_parent_and_cluster(self):
        specs = [
            {"id": "a", "cluster": "c1", "parent_id": ""},
            {"id": "b", "cluster": "c1", "parent_id": "a"},
        ]
        engine = {"projection": {"nodes": {}, "links": []}}
        adj = self._service(engine).build_adjacency(specs, engine)
        self.assertIn("b", adj["a"])
        self.assertIn("a", adj["b"])

    def test_spread_activation_propagates_hop1(self):
        service = self._service({"projection": {"nodes": {}, "links": []}})
        specs = [{"id": "seed", "cluster": "s"}, {"id": "hop1", "cluster": "s", "parent_id": "seed"}]
        adj = service.build_adjacency(specs, {"projection": {"nodes": {}, "links": []}})
        scores = {"seed": 0.0, "hop1": 0.0}
        service.spread_activation({"seed"}, adj, scores)
        self.assertGreater(scores["seed"], 0.9)
        self.assertGreater(scores["hop1"], 0.4)

    def test_match_seed_ids_finds_title_substring(self):
        service = self._service({"projection": {"nodes": {}, "links": []}})
        specs = [{"id": "n1", "title": "asyncio"}]
        seeds = service.match_seed_ids("discuss asyncio today", specs)
        self.assertIn("n1", seeds)

    def test_collect_node_specs_with_circular_block_data(self):
        """Regression: dict membership on blocks must not recurse on circular refs."""
        circular: dict = {"content": "nested"}
        circular["self"] = circular
        blocks = [
            {"block_id": f"b{i}", "label": "episodic", "data": {"content": f"block-{i}"}}
            for i in range(120)
        ]
        blocks[-1]["data"] = circular
        engine = {
            "state": type("GoalState", (), {"goal": {"current": "test", "progress": 0.0}})(),
            "memory_store": type("Store", (), {"blocks": blocks})(),
            "trace": [],
            "projection": {"nodes": {}, "links": []},
        }
        specs = self._service(engine).collect()
        ids = {s.get("id") for s in specs}
        self.assertIn("b100", ids)
        self.assertTrue(any(str(i).startswith("kw-b119") for i in ids))


if __name__ == "__main__":
    unittest.main()
