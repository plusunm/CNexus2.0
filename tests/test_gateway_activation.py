"""Tests for spreading-activation injection service."""

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
    activation_mod = load(f"{pkg}.services.activation", os.path.join("services", "activation.py"))
    return state_mod, activation_mod


class ActivationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.activation_mod = _load_modules()

    def _service(self, specs, scores=None):
        engine = {"activation": {"scores": dict(scores or {})}}

        return self.activation_mod.ActivationService(
            self.state_mod.EngineStateManager(engine),
            self.activation_mod.ActivationHooks(
                collect_node_specs=lambda: list(specs),
            ),
            default_threshold=0.4,
            default_inject_limit=2,
        )

    def test_threshold_filters_and_sorts(self):
        specs = [
            {"id": "a", "title": "Alpha", "tag": "term", "desc": "aaa"},
            {"id": "b", "title": "Beta", "tag": "term", "desc": "bbb"},
            {"id": "c", "title": "Gamma", "tag": "term", "desc": "ccc"},
        ]
        service = self._service(specs, scores={"a": 0.5, "b": 0.9, "c": 0.1})
        hits = service.threshold_activated_fragments(limit=2, threshold=0.4)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0][1]["id"], "b")
        self.assertEqual(hits[1][1]["id"], "a")

    def test_zero_limit_returns_empty(self):
        service = self._service([], scores={})
        self.assertEqual(service.threshold_activated_fragments(limit=0), [])

    def test_memory_scope_filters_remote_nodes(self):
        specs = [
            {"id": "local", "title": "Local", "source_peer": ""},
            {"id": "peer", "title": "Peer", "source_peer": "peer-a"},
        ]
        service = self._service(specs, scores={"local": 0.9, "peer": 0.9})
        local_hits = service.threshold_activated_fragments(
            memory_scope="local",
            trusted_peers=["peer-a"],
        )
        self.assertEqual(len(local_hits), 1)
        self.assertEqual(local_hits[0][1]["id"], "local")


if __name__ == "__main__":
    unittest.main()
