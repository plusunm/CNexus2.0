"""Tests for system probe service."""

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

    path = os.path.join(GATEWAY_DIR, "services", "system_probe.py")
    spec = importlib.util.spec_from_file_location(f"{pkg}.services.system_probe", path)
    state_path = os.path.join(GATEWAY_DIR, "state.py")
    state_spec = importlib.util.spec_from_file_location(f"{pkg}.state", state_path)
    state_mod = importlib.util.module_from_spec(state_spec)
    state_mod.__package__ = pkg
    sys.modules[f"{pkg}.state"] = state_mod
    assert state_spec.loader is not None
    state_spec.loader.exec_module(state_mod)

    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.system_probe"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return state_mod, mod


class SystemProbeServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.probe_mod = _load_modules()

    def test_gateway_health_ready(self):
        engine = {"started_at": 1_700_000_000.0, "memory_store": type("S", (), {"blocks": []})()}
        svc = self.probe_mod.SystemProbeService(self.state_mod.EngineStateManager(engine))
        health = svc.gateway_health()
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["operational_ready"])

    def test_memory_stats_counts_blocks(self):
        engine = {"started_at": 1_700_000_000.0, "memory_store": type("S", (), {"blocks": [1, 2]})()}
        svc = self.probe_mod.SystemProbeService(self.state_mod.EngineStateManager(engine))
        stats = svc.memory_stats()
        self.assertEqual(stats["total"], 2)


if __name__ == "__main__":
    unittest.main()
