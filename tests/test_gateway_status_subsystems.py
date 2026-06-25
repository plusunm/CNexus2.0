"""Tests for status subsystems service."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
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

    state_path = os.path.join(GATEWAY_DIR, "state.py")
    state_spec = importlib.util.spec_from_file_location(f"{pkg}.state", state_path)
    state_mod = importlib.util.module_from_spec(state_spec)
    state_mod.__package__ = pkg
    sys.modules[f"{pkg}.state"] = state_mod
    assert state_spec.loader is not None
    state_spec.loader.exec_module(state_mod)

    path = os.path.join(GATEWAY_DIR, "services", "status_subsystems.py")
    spec = importlib.util.spec_from_file_location(f"{pkg}.services.status_subsystems", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.status_subsystems"] = mod

    for fname, modname in (
        ("consolidation_status.py", "consolidation_status"),
        ("replay_status.py", "replay_status"),
        ("awakening_status.py", "awakening_status"),
        ("pruning_status.py", "pruning_status"),
        ("entropy_status.py", "entropy_status"),
        ("persistence_status.py", "persistence_status"),
        ("negotiation_conflict_status.py", "negotiation_conflict_status"),
        ("reflection_status.py", "reflection_status"),
        ("conflict_resolution_status.py", "conflict_resolution_status"),
    ):
        p = os.path.join(GATEWAY_DIR, "services", fname)
        s = importlib.util.spec_from_file_location(f"{pkg}.services.{modname}", p)
        m = importlib.util.module_from_spec(s)
        m.__package__ = f"{pkg}.services"
        sys.modules[f"{pkg}.services.{modname}"] = m
        assert s.loader is not None
        s.loader.exec_module(m)

    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return state_mod, mod


class StatusSubsystemsServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.subsystems_mod = _load_modules()

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.persist_path = os.path.join(self._tmpdir.name, "state.json")
        with open(self.persist_path, "w", encoding="utf-8") as f:
            f.write("{}")
        self.engine = {
            "memory_store": type("MS", (), {"blocks": [{"label": "semantic"}, {"block_id": "sem-rem-1"}]})(),
            "trace": [1, 2],
            "projection": {"nodes": {"a": {}}, "links": []},
            "consolidation": {"last_shallow_at": 123.0},
            "negotiation_conflicts": [{"at": 1, "resolutions": [{"block_id": "b1", "status": "merged"}]}],
        }

    def tearDown(self):
        self._tmpdir.cleanup()

    def _service(self):
        state = self.state_mod.EngineStateManager(self.engine)
        m = sys.modules
        return self.subsystems_mod.StatusSubsystemsService(
            m["cnexus_gateway.services.persistence_status"].PersistenceStatusService(
                state,
                m["cnexus_gateway.services.persistence_status"].PersistenceStatusHooks(
                    persist_version="test-v1",
                    persist_file_path=lambda: self.persist_path,
                    persist_meta=lambda: {"saved_at": 1.0, "loaded_at": 2.0},
                ),
            ),
            m["cnexus_gateway.services.consolidation_status"].ConsolidationStatusService(
                state,
                m["cnexus_gateway.services.consolidation_status"].ConsolidationStatusHooks(
                    rem_consolidation_status=lambda c, ctx: {"enabled": True, "phase": "idle"},
                    build_rem_context=lambda: {"specs": []},
                ),
            ),
            m["cnexus_gateway.services.negotiation_conflict_status"].NegotiationConflictStatusService(
                state,
                m["cnexus_gateway.services.negotiation_conflict_status"].NegotiationConflictStatusHooks(
                    negotiation_conflict_enabled=lambda: True,
                    negotiation_conflict_use_llm=lambda: False,
                    negotiation_conflict_context=lambda: "ctx",
                ),
            ),
            m["cnexus_gateway.services.reflection_status"].ReflectionStatusService(
                m["cnexus_gateway.services.reflection_status"].ReflectionStatusHooks(
                    reflection_engine_status=lambda: {"enabled": True},
                )
            ),
            m["cnexus_gateway.services.replay_status"].ReplayStatusService(
                state,
                m["cnexus_gateway.services.replay_status"].ReplayStatusHooks(
                    get_log_replay_engine=lambda: None,
                    get_audit_log=lambda: None,
                    get_state_reconstructor=lambda: None,
                ),
            ),
            m["cnexus_gateway.services.awakening_status"].AwakeningStatusService(
                m["cnexus_gateway.services.awakening_status"].AwakeningStatusHooks(
                    read_awakening_base=lambda: {"phase": "idle", "label": "idle", "progress": 0.0, "alive": True},
                    genesis_status=lambda: {"enabled": False},
                    reconstructor_status=lambda: {},
                )
            ),
            m["cnexus_gateway.services.pruning_status"].PruningStatusService(
                m["cnexus_gateway.services.pruning_status"].PruningStatusHooks(
                    get_cognitive_pruning_engine=lambda: None,
                )
            ),
            m["cnexus_gateway.services.entropy_status"].EntropyStatusService(
                m["cnexus_gateway.services.entropy_status"].EntropyStatusHooks(
                    get_entropy_store=lambda: False,
                    get_peer_registry=lambda: None,
                )
            ),
            m["cnexus_gateway.services.conflict_resolution_status"].ConflictResolutionStatusService(
                state,
                m["cnexus_gateway.services.conflict_resolution_status"].ConflictResolutionStatusHooks(
                    conflict_agent_status=lambda: {"enabled": True},
                    negotiation_conflict_enabled=lambda: True,
                    negotiation_conflict_use_llm=lambda: False,
                ),
            ),
        )

    def test_persistence_status(self):
        status = self._service().persistence_status()
        self.assertTrue(status["exists"])
        self.assertEqual(status["memory_blocks"], 2)

    def test_consolidation_status(self):
        status = self._service().consolidation_status()
        self.assertEqual(status["semantic_facts"], 2)
        self.assertEqual(status["last_shallow_at"], 123.0)

    def test_negotiation_conflict_recent(self):
        status = self._service().negotiation_conflict_recent()
        self.assertEqual(status["count"], 1)
        self.assertEqual(status["items"][0]["pairs"][0]["block_id"], "b1")

    def test_reflection_status(self):
        self.assertTrue(self._service().reflection_status()["enabled"])

    def test_replay_status_disabled(self):
        self.assertFalse(self._service().replay_status()["enabled"])

    def test_conflict_resolution_status(self):
        status = self._service().conflict_resolution_status()
        self.assertTrue(status["enabled"])
        self.assertEqual(status["negotiation_conflict_buffer"], 1)

    def test_awakening_status(self):
        status = self._service().awakening_status()
        self.assertEqual(status["phase"], "idle")

    def test_pruning_status_unavailable(self):
        self.assertFalse(self._service().pruning_status()["enabled"])

    def test_entropy_status_disabled(self):
        self.assertFalse(self._service().entropy_status()["enabled"])


if __name__ == "__main__":
    unittest.main()
