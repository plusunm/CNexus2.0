"""Tests for control bootstrap factory."""

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
    for fname in (
        "conflict_control.py",
        "pruning_control.py",
        "consensus_control.py",
        "memory_control.py",
        "replay_control.py",
        "reflection_control.py",
        "rem_control.py",
        "control_plane.py",
    ):
        load(f"{pkg}.services.{fname[:-3]}", fname)

    return load(f"{pkg}.services.control_bootstrap", "control_bootstrap.py")


class _ShadowStub:
    def cse_synthesize(self, window=200):
        return {"window": window}


class ControlBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap_mod = _load_modules()

    def _hooks(self):
        m = sys.modules

        def noop(*a, **k):
            return None

        def empty_dict(*a, **k):
            return {}

        return self.bootstrap_mod.ControlBootstrapHooks(
            conflict=m["cnexus_gateway.services.conflict_control"].ConflictControlHooks(
                get_conflict_agent=lambda: None,
                run_conflict_resolution=empty_dict,
                conflict_resolution_status=empty_dict,
                set_negotiation_conflict_llm=noop,
                set_negotiation_conflict_enabled=noop,
            ),
            pruning=m["cnexus_gateway.services.pruning_control"].PruningControlHooks(
                get_pruning_engine=lambda: None,
            ),
            consensus=m["cnexus_gateway.services.consensus_control"].ConsensusControlHooks(
                get_reputation_registry=lambda: None,
                get_network_firewall=lambda: None,
                audit_event=noop,
            ),
            memory=m["cnexus_gateway.services.memory_control"].MemoryControlHooks(
                audit_event=noop,
                get_current_model_registry=lambda: {},
                default_model_registry=lambda: {},
                reset_engine_memory=noop,
                persist_file_path=lambda: "",
                append_runtime_log=noop,
                persist_engine_state=noop,
                persistence_status=empty_dict,
            ),
            replay=m["cnexus_gateway.services.replay_control"].ReplayControlHooks(
                run_log_replay=empty_dict,
            ),
            reflection=m["cnexus_gateway.services.reflection_control"].ReflectionControlHooks(
                run_self_reflection=empty_dict,
            ),
            rem=m["cnexus_gateway.services.rem_control"].RemControlHooks(
                run_rem_deep_sleep=lambda force=False: {"ok": True, "force": force},
            ),
        )

    def test_build_control_services_composes_plane(self):
        bundle = self.bootstrap_mod.build_control_services(_ShadowStub(), self._hooks())
        self.assertIsNotNone(bundle.control_plane)
        self.assertIsNotNone(bundle.rem)
        out = bundle.control_plane.rem_sleep({"force": True})
        self.assertTrue(out["force"])
        synth = bundle.control_plane.cse_synthesize({"window": 42})
        self.assertEqual(synth["window"], 42)


if __name__ == "__main__":
    unittest.main()
