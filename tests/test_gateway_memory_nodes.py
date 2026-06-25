"""Tests for memory node spec service."""

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
    load(f"{pkg}.services.converse_speech", os.path.join("services", "converse_speech.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.wormhole_embed", os.path.join("services", "memory", "wormhole_embed.py"))
    load(f"{pkg}.services.memory.graph", os.path.join("services", "memory", "graph.py"))
    nodes_mod = load(f"{pkg}.services.memory_nodes", os.path.join("services", "memory_nodes.py"))
    return state_mod, nodes_mod


class _FakeGoalState:
    goal = {"current": "test goal", "progress": 0.5}


class _FakeStore:
    def __init__(self, blocks):
        self.blocks = blocks


class MemoryNodeSpecServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.nodes_mod = _load_modules()

    def _service(self, engine):
        return self.nodes_mod.MemoryNodeSpecService(
            self.state_mod.EngineStateManager(engine),
            self.nodes_mod.MemoryNodeSpecHooks(
                extract_keywords=lambda text, limit: [text[:3]] if text else [],
            ),
            config=self.nodes_mod.MemoryGraphConfig(
                max_items=64,
                recent_blocks=20,
                recent_trace=14,
            ),
        )

    def test_collect_includes_goal_and_block(self):
        engine = {
            "state": _FakeGoalState(),
            "memory_store": _FakeStore([{"block_id": "b1", "label": "episodic", "data": {"content": "hello memory"}}]),
            "trace": [],
            "projection": {"nodes": {}, "links": []},
        }
        specs = self._service(engine).collect()
        ids = {s["id"] for s in specs}
        self.assertIn("goal-current", ids)
        self.assertIn("b1", ids)

    def test_collect_includes_trace_episode(self):
        engine = {
            "state": _FakeGoalState(),
            "memory_store": _FakeStore([]),
            "trace": [{"trace_id": "t1", "input": "user question", "speech": {"text": "answer"}, "decision": {}}],
            "projection": {"nodes": {}, "links": []},
        }
        specs = self._service(engine).collect()
        self.assertTrue(any(s["id"] == "t1" for s in specs))

    def test_respects_max_items(self):
        blocks = [
            {"block_id": f"b{i}", "label": "episodic", "data": {"content": f"block {i}"}}
            for i in range(100)
        ]
        engine = {
            "state": _FakeGoalState(),
            "memory_store": _FakeStore(blocks),
            "trace": [],
            "projection": {"nodes": {}, "links": []},
        }
        service = self.nodes_mod.MemoryNodeSpecService(
            self.state_mod.EngineStateManager(engine),
            self.nodes_mod.MemoryNodeSpecHooks(
                extract_keywords=lambda text, limit: [text[:3]] if text else [],
            ),
            config=self.nodes_mod.MemoryGraphConfig(max_items=5),
        )
        self.assertLessEqual(len(service.collect()), 5)


if __name__ == "__main__":
    unittest.main()
