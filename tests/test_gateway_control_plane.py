"""Tests for control plane service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
SRC_DIR = os.path.join(ROOT, "src")


def _load_modules():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)

    def load(name, filename):
        path = os.path.join(GATEWAY_DIR, "services", filename)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = f"{pkg}.services"
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    load(f"{pkg}.services.status_snapshot", "status_snapshot.py")
    load(f"{pkg}.services.shadow_projection", "shadow_projection.py")
    load(f"{pkg}.services.conflict_control", "conflict_control.py")
    load(f"{pkg}.services.pruning_control", "pruning_control.py")
    load(f"{pkg}.services.consensus_control", "consensus_control.py")
    load(f"{pkg}.services.memory_control", "memory_control.py")
    load(f"{pkg}.services.replay_control", "replay_control.py")
    load(f"{pkg}.services.reflection_control", "reflection_control.py")
    load(f"{pkg}.services.rem_control", "rem_control.py")
    return load(f"{pkg}.services.control_plane", "control_plane.py")


class _ShadowStub:
    def cse_synthesize(self, window=200):
        return {"window": window, "narrative": "synth"}

    def ollama_start(self):
        return {"ok": True, "running": True}

    def ollama_stop(self):
        return {"ok": True, "running": False}


class _MemoryStub:
    def clear(self, *, keep_models=True):
        return {"cleared": True, "keep_models": keep_models}


class _ReplayStub:
    def run(self, data):
        return {"replay": bool(data.get("force"))}


class _ReflectionStub:
    def reflect_meta(self, data):
        return {"meta": bool(data)}


class _RemStub:
    def run(self, data):
        return {"rem": bool(data.get("force"))}


class _ConflictStub:
    def resolve(self, data):
        return {"resolved": True}, 200

    def update_settings(self, data):
        return {"settings": data}, 200


class _PruningStub:
    def run(self, data):
        return {"pruned": True}, 200


class _ConsensusStub:
    def update_reputation(self, data):
        return {"rep": 1}, 200


class ControlPlaneServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control_mod = _load_modules()

    def _service(self):
        return self.control_mod.ControlPlaneService(
            _ShadowStub(),
            _MemoryStub(),
            _ReplayStub(),
            _ReflectionStub(),
            _RemStub(),
            _ConflictStub(),
            _PruningStub(),
            _ConsensusStub(),
        )

    def test_memory_clear_parses_keep_models(self):
        out = self._service().memory_clear({"keep_models": "false"})
        self.assertFalse(out["keep_models"])

    def test_conflict_resolve_delegates(self):
        payload, status = self._service().conflict_resolve({"mode": "emergent"})
        self.assertEqual(status, 200)

    def test_cse_synthesize_delegates_shadow(self):
        out = self._service().cse_synthesize({"window": 50})
        self.assertEqual(out["window"], 50)


if __name__ == "__main__":
    unittest.main()
