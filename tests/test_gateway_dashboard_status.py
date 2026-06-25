"""Tests for dashboard status service."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
API_DIR = os.path.join(ROOT, "src", "api")


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

    subsystems_path = os.path.join(GATEWAY_DIR, "services", "status_subsystems.py")
    subsystems_spec = importlib.util.spec_from_file_location(
        f"{pkg}.services.status_subsystems", subsystems_path
    )
    subsystems_mod = importlib.util.module_from_spec(subsystems_spec)
    subsystems_mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.status_subsystems"] = subsystems_mod

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

    assert subsystems_spec.loader is not None
    subsystems_spec.loader.exec_module(subsystems_mod)

    consolidation_mod = sys.modules[f"{pkg}.services.consolidation_status"]
    replay_mod = sys.modules[f"{pkg}.services.replay_status"]
    awakening_mod = sys.modules[f"{pkg}.services.awakening_status"]
    pruning_mod = sys.modules[f"{pkg}.services.pruning_status"]
    entropy_mod = sys.modules[f"{pkg}.services.entropy_status"]

    persistence_mod = sys.modules[f"{pkg}.services.persistence_status"]
    negotiation_conflict_mod = sys.modules[f"{pkg}.services.negotiation_conflict_status"]
    reflection_mod = sys.modules[f"{pkg}.services.reflection_status"]
    conflict_resolution_mod = sys.modules[f"{pkg}.services.conflict_resolution_status"]

    dashboard_path = os.path.join(GATEWAY_DIR, "services", "dashboard_status.py")
    dashboard_spec = importlib.util.spec_from_file_location(
        f"{pkg}.services.dashboard_status", dashboard_path
    )
    dashboard_mod = importlib.util.module_from_spec(dashboard_spec)
    dashboard_mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.dashboard_status"] = dashboard_mod
    assert dashboard_spec.loader is not None
    dashboard_spec.loader.exec_module(dashboard_mod)

    identity_mod = importlib.util.spec_from_file_location(
        f"{pkg}.services.identity_status", os.path.join(GATEWAY_DIR, "services", "identity_status.py")
    )
    identity_mod_obj = importlib.util.module_from_spec(identity_mod)
    identity_mod_obj.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.identity_status"] = identity_mod_obj
    assert identity_mod.loader is not None
    identity_mod.loader.exec_module(identity_mod_obj)

    audit_mod = importlib.util.spec_from_file_location(
        f"{pkg}.services.audit_chain_status", os.path.join(GATEWAY_DIR, "services", "audit_chain_status.py")
    )
    audit_mod_obj = importlib.util.module_from_spec(audit_mod)
    audit_mod_obj.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.audit_chain_status"] = audit_mod_obj
    assert audit_mod.loader is not None
    audit_mod.loader.exec_module(audit_mod_obj)

    consensus_mod = importlib.util.spec_from_file_location(
        f"{pkg}.services.consensus_status", os.path.join(GATEWAY_DIR, "services", "consensus_status.py")
    )
    consensus_mod_obj = importlib.util.module_from_spec(consensus_mod)
    consensus_mod_obj.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.consensus_status"] = consensus_mod_obj
    assert consensus_mod.loader is not None
    consensus_mod.loader.exec_module(consensus_mod_obj)

    metrics_spec = importlib.util.spec_from_file_location("metrics", os.path.join(API_DIR, "metrics.py"))
    metrics_mod = importlib.util.module_from_spec(metrics_spec)
    assert metrics_spec.loader is not None
    metrics_spec.loader.exec_module(metrics_mod)
    return state_mod, subsystems_mod, consolidation_mod, replay_mod, awakening_mod, pruning_mod, entropy_mod, persistence_mod, negotiation_conflict_mod, reflection_mod, conflict_resolution_mod, dashboard_mod, identity_mod_obj, audit_mod_obj, consensus_mod_obj, metrics_mod


class _Audit:
    last_hash = "abc123"

    def entry_count(self):
        return 3


class DashboardStatusServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.subsystems_mod, cls.consolidation_mod, cls.replay_mod, cls.awakening_mod, cls.pruning_mod, cls.entropy_mod, cls.persistence_mod, cls.negotiation_conflict_mod, cls.reflection_mod, cls.conflict_resolution_mod, cls.dashboard_mod, cls.identity_mod, cls.audit_mod, cls.consensus_mod, cls.metrics_mod = _load_modules()

    def _service(self, *, metrics=None):
        started = time.time() - 120
        engine = {
            "started_at": started,
            "memory_store": type("MS", (), {"blocks": [{"label": "episode"}, {"label": "semantic"}, {"block_id": "sem-rem-2"}]})(),
            "trace": [1],
            "current_iteration": 7,
            "consolidation": {},
        }
        metrics = metrics if metrics is not None else self.metrics_mod

        state = self.state_mod.EngineStateManager(engine)
        subsystems = self.subsystems_mod.StatusSubsystemsService(
            self.persistence_mod.PersistenceStatusService(
                state,
                self.persistence_mod.PersistenceStatusHooks(
                    persist_version="v1",
                    persist_file_path=lambda: os.path.join(ROOT, "missing.json"),
                    persist_meta=lambda: {},
                ),
            ),
            self.consolidation_mod.ConsolidationStatusService(
                state,
                self.consolidation_mod.ConsolidationStatusHooks(
                    rem_consolidation_status=lambda c, ctx: {"enabled": True, "running": False},
                    build_rem_context=lambda: {},
                ),
            ),
            self.negotiation_conflict_mod.NegotiationConflictStatusService(
                state,
                self.negotiation_conflict_mod.NegotiationConflictStatusHooks(
                    negotiation_conflict_enabled=lambda: False,
                    negotiation_conflict_use_llm=lambda: False,
                    negotiation_conflict_context=lambda: "",
                ),
            ),
            self.reflection_mod.ReflectionStatusService(
                self.reflection_mod.ReflectionStatusHooks(
                    reflection_engine_status=lambda: {"enabled": True},
                )
            ),
            self.replay_mod.ReplayStatusService(
                state,
                self.replay_mod.ReplayStatusHooks(
                    get_log_replay_engine=lambda: None,
                    get_audit_log=lambda: None,
                    get_state_reconstructor=lambda: None,
                ),
            ),
            self.awakening_mod.AwakeningStatusService(
                self.awakening_mod.AwakeningStatusHooks(
                    read_awakening_base=lambda: {"phase": "idle"},
                    genesis_status=lambda: {},
                    reconstructor_status=lambda: {},
                )
            ),
            self.pruning_mod.PruningStatusService(
                self.pruning_mod.PruningStatusHooks(get_cognitive_pruning_engine=lambda: None)
            ),
            self.entropy_mod.EntropyStatusService(
                self.entropy_mod.EntropyStatusHooks(
                    get_entropy_store=lambda: None,
                    get_peer_registry=lambda: None,
                )
            ),
            self.conflict_resolution_mod.ConflictResolutionStatusService(
                state,
                self.conflict_resolution_mod.ConflictResolutionStatusHooks(
                    conflict_agent_status=lambda: {"enabled": True},
                    negotiation_conflict_enabled=lambda: False,
                    negotiation_conflict_use_llm=lambda: False,
                ),
            ),
        )

        identity = self.identity_mod.IdentityStatusService(
            self.identity_mod.IdentityStatusHooks(
                identity_optional=False,
                identity_key_path=lambda: "/tmp/id",
                get_identity_manager=lambda: type("IM", (), {"public_key_hex": lambda self: "pk-test"})(),
            )
        )
        audit = self.audit_mod.AuditChainStatusService(
            self.audit_mod.AuditChainStatusHooks(
                audit_optional=False,
                audit_log_path=lambda: "/tmp/audit.log",
                get_audit_log=lambda: _Audit(),
                get_audit_integrity=lambda: {"ok": True},
            )
        )
        consensus = self.consensus_mod.ConsensusStatusService(
            self.consensus_mod.ConsensusStatusHooks(
                get_negotiation_manager=lambda: type("N", (), {"status": lambda self: {"mode": "personal"}})(),
                get_reputation_registry=lambda: type("R", (), {"get_all": lambda self: {}})(),
            )
        )

        return self.dashboard_mod.DashboardStatusService(
            self.state_mod.EngineStateManager(engine),
            subsystems,
            identity,
            audit,
            consensus,
            self.dashboard_mod.DashboardStatusHooks(
                get_metrics_module=lambda: metrics,
                get_audit_log=lambda: _Audit(),
                get_gossip_sync=lambda: None,
                get_peer_registry=lambda: None,
                heartbeat_stale_seconds=lambda: 120.0,
                server_port=7864,
            ),
        )

    def test_build_ok_payload(self):
        payload = self._service().build()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["schema_version"], "2.0-mission-control")
        self.assertEqual(payload["node"]["pubkey"], "pk-test")
        self.assertEqual(payload["node"]["memory_blocks"], 3)
        self.assertTrue(payload["rem"]["enabled"])
        self.assertEqual(payload["awakening"]["phase"], "idle")

    def test_metrics_unavailable(self):
        payload = self._service(metrics=False).build()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "metrics_unavailable")


if __name__ == "__main__":
    unittest.main()
