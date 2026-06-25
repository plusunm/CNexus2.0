"""Tests for L0 status snapshot service."""

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

    def load(name, filename):
        path = os.path.join(GATEWAY_DIR, "services", filename)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = f"{pkg}.services"
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_path = os.path.join(GATEWAY_DIR, "state.py")
    state_spec = importlib.util.spec_from_file_location(f"{pkg}.state", state_path)
    state_mod = importlib.util.module_from_spec(state_spec)
    state_mod.__package__ = pkg
    sys.modules[f"{pkg}.state"] = state_mod
    assert state_spec.loader is not None
    state_spec.loader.exec_module(state_mod)

    subsystems_mod = load(f"{pkg}.services.status_subsystems", "status_subsystems.py")
    consolidation_mod = load(f"{pkg}.services.consolidation_status", "consolidation_status.py")
    replay_mod = load(f"{pkg}.services.replay_status", "replay_status.py")
    awakening_mod = load(f"{pkg}.services.awakening_status", "awakening_status.py")
    pruning_mod = load(f"{pkg}.services.pruning_status", "pruning_status.py")
    entropy_mod = load(f"{pkg}.services.entropy_status", "entropy_status.py")
    persistence_mod = load(f"{pkg}.services.persistence_status", "persistence_status.py")
    negotiation_conflict_mod = load(f"{pkg}.services.negotiation_conflict_status", "negotiation_conflict_status.py")
    reflection_mod = load(f"{pkg}.services.reflection_status", "reflection_status.py")
    conflict_resolution_mod = load(f"{pkg}.services.conflict_resolution_status", "conflict_resolution_status.py")
    network_mod = load(f"{pkg}.services.network_status", "network_status.py")
    peers_mod = load(f"{pkg}.services.peers_status", "peers_status.py")
    audit_mod = load(f"{pkg}.services.audit_chain_status", "audit_chain_status.py")
    resilience_mod = load(f"{pkg}.services.resilience_status", "resilience_status.py")
    identity_mod = load(f"{pkg}.services.identity_status", "identity_status.py")
    api_auth_mod = load(f"{pkg}.services.api_auth_status", "api_auth_status.py")
    consensus_mod = load(f"{pkg}.services.consensus_status", "consensus_status.py")
    assets_mod = load(f"{pkg}.services.assets_status", "assets_status.py")
    activation_mod = load(f"{pkg}.services.activation", "activation.py")
    snapshot_mod = load(f"{pkg}.services.status_snapshot", "status_snapshot.py")
    return (
        state_mod,
        subsystems_mod,
        consolidation_mod,
        replay_mod,
        awakening_mod,
        pruning_mod,
        entropy_mod,
        persistence_mod,
        negotiation_conflict_mod,
        reflection_mod,
        conflict_resolution_mod,
        network_mod,
        peers_mod,
        audit_mod,
        resilience_mod,
        identity_mod,
        api_auth_mod,
        consensus_mod,
        assets_mod,
        activation_mod,
        snapshot_mod,
    )


class _Emotion:
    val = 0.1
    arousal = 0.2
    dominance = 0.3


class _State:
    emotion = _Emotion()
    goal = {"current": "learn", "progress": 0.4}
    meta = {"active_intent": "converse", "weight": 3}
    relationship = {"closeness": 0.6}


class _Stub:
    def build(self):
        return {"ok": True}


class StatusSnapshotServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.state_mod,
            cls.subsystems_mod,
            cls.consolidation_mod,
            cls.replay_mod,
            cls.awakening_mod,
            cls.pruning_mod,
            cls.entropy_mod,
            cls.persistence_mod,
            cls.negotiation_conflict_mod,
            cls.reflection_mod,
            cls.conflict_resolution_mod,
            cls.network_mod,
            cls.peers_mod,
            cls.audit_mod,
            cls.resilience_mod,
            cls.identity_mod,
            cls.api_auth_mod,
            cls.consensus_mod,
            cls.assets_mod,
            cls.activation_mod,
            cls.snapshot_mod,
        ) = _load_modules()

    def _subsystems(self, engine):
        state = self.state_mod.EngineStateManager(engine)
        consolidation = self.consolidation_mod.ConsolidationStatusService(
            state,
            self.consolidation_mod.ConsolidationStatusHooks(
                rem_consolidation_status=lambda c, ctx: {"consolidation": True},
                build_rem_context=lambda: {},
            ),
        )
        replay = self.replay_mod.ReplayStatusService(
            state,
            self.replay_mod.ReplayStatusHooks(
                get_log_replay_engine=lambda: None,
                get_audit_log=lambda: None,
                get_state_reconstructor=lambda: None,
            ),
        )
        awakening = self.awakening_mod.AwakeningStatusService(
            self.awakening_mod.AwakeningStatusHooks(
                read_awakening_base=lambda: {},
                genesis_status=lambda: {},
                reconstructor_status=lambda: {},
            )
        )
        pruning = self.pruning_mod.PruningStatusService(
            self.pruning_mod.PruningStatusHooks(get_cognitive_pruning_engine=lambda: None)
        )
        entropy = self.entropy_mod.EntropyStatusService(
            self.entropy_mod.EntropyStatusHooks(
                get_entropy_store=lambda: None,
                get_peer_registry=lambda: None,
            )
        )
        return self.subsystems_mod.StatusSubsystemsService(
            self.persistence_mod.PersistenceStatusService(
                state,
                self.persistence_mod.PersistenceStatusHooks(
                    persist_version="test-v1",
                    persist_file_path=lambda: os.path.join(ROOT, "missing.json"),
                    persist_meta=lambda: {},
                ),
            ),
            consolidation,
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
                    reflection_engine_status=lambda: {"reflection": True},
                )
            ),
            replay,
            awakening,
            pruning,
            entropy,
            self.conflict_resolution_mod.ConflictResolutionStatusService(
                state,
                self.conflict_resolution_mod.ConflictResolutionStatusHooks(
                    conflict_agent_status=lambda: {},
                    negotiation_conflict_enabled=lambda: False,
                    negotiation_conflict_use_llm=lambda: False,
                ),
            ),
        )

    def _service(self, *, overview_items=None):
        engine = {
            "state": _State(),
            "memory_store": type("MS", (), {"blocks": [{"label": "episode"}, {"label": "semantic"}]})(),
            "current_iteration": 5,
            "activation": {
                "scores": {"n1": 0.5},
                "wormhole_links": [{"source": "a", "target": "b", "similarity": 0.9, "energy": 0.5}],
            },
            "projection": {"nodes": {}, "links": [{"source": "x", "target": "y", "type": "relates"}]},
            "consolidation": {},
        }
        items = overview_items if overview_items is not None else [
            {"id": "n1", "title": "episode one", "tag": "episode", "score": 0.5, "activity": 0.5, "is_active": True},
        ]
        network = self.network_mod.NetworkStatusService(
            self.network_mod.NetworkStatusHooks(
                get_connectivity_manager=lambda: None,
                get_dht_service=lambda: None,
                get_network_firewall=lambda: None,
            )
        )
        peers = self.peers_mod.PeersStatusService(
            self.peers_mod.PeersStatusHooks(
                peer_registry_path=lambda: "/tmp/peers.json",
                get_peer_registry=lambda: None,
                get_gossip_sync=lambda: None,
            ),
            network,
        )
        audit = self.audit_mod.AuditChainStatusService(
            self.audit_mod.AuditChainStatusHooks(
                audit_optional=False,
                audit_log_path=lambda: "/tmp/audit.log",
                get_audit_log=lambda: None,
                get_audit_integrity=lambda: {"ok": True},
            )
        )
        resilience = self.resilience_mod.ResilienceStatusService(
            self.resilience_mod.ResilienceStatusHooks(
                get_metrics_module=lambda: False,
                get_gossip_sync=lambda: None,
                get_peer_registry=lambda: None,
                heartbeat_stale_seconds=lambda: 120.0,
            ),
            audit,
        )
        identity = self.identity_mod.IdentityStatusService(
            self.identity_mod.IdentityStatusHooks(
                identity_optional=False,
                identity_key_path=lambda: "/tmp/id",
                get_identity_manager=lambda: None,
            )
        )
        api_auth = self.api_auth_mod.ApiAuthStatusService(
            self.api_auth_mod.ApiAuthStatusHooks(get_auth_middleware=lambda: None)
        )
        consensus = self.consensus_mod.ConsensusStatusService(
            self.consensus_mod.ConsensusStatusHooks(
                get_negotiation_manager=lambda: None,
                get_reputation_registry=lambda: None,
            )
        )
        assets = self.assets_mod.AssetsStatusService(
            self.assets_mod.AssetsStatusHooks(
                asset_embed_enabled=lambda: False,
                clip_enabled=lambda: False,
                asset_peer_push_enabled=lambda: False,
                asset_peer_pull_enabled=lambda: False,
                get_asset_vector_index=lambda: None,
                get_asset_peer_sync=lambda: None,
                get_asset_push_queue=lambda: None,
                get_asset_processor=lambda: None,
            )
        )
        activation = self.activation_mod.ActivationService(
            self.state_mod.EngineStateManager(engine),
            self.activation_mod.ActivationHooks(
                collect_node_specs=lambda: items,
            ),
            default_threshold=0.4,
            default_inject_limit=3,
        )
        return self.snapshot_mod.StatusSnapshotService(
            self.state_mod.EngineStateManager(engine),
            self._subsystems(engine),
            peers,
            resilience,
            identity,
            audit,
            api_auth,
            consensus,
            assets,
            activation,
        )

    def test_schema_and_core_fields(self):
        payload = self._service().build()
        self.assertEqual(payload["schema_version"], "2.0")
        self.assertEqual(payload["status"], "online")
        self.assertEqual(payload["memory_count"], 2)
        self.assertEqual(payload["goal"]["current"], "learn")
        self.assertEqual(payload["emotion"]["valence"], 0.1)

    def test_memory_items_and_feeds(self):
        payload = self._service().build()
        self.assertEqual(len(payload["memory_items"]), 1)
        self.assertEqual(payload["feeds"]["episodic"][0]["text"], "episode one")

    def test_wormhole_and_projection_links(self):
        payload = self._service().build()
        self.assertEqual(payload["wormhole_links"][0]["source"], "a")
        self.assertEqual(payload["projection_links"][0]["type"], "relates")

    def test_sub_status_services_merged(self):
        payload = self._service().build()
        self.assertTrue(payload["consolidation"]["consolidation"])
        self.assertFalse(payload["replay"]["enabled"])
        self.assertTrue(payload["reflection"]["reflection"])
        self.assertEqual(payload["resilience"]["label"], "solo")
        self.assertFalse(payload["node_identity"]["loaded"])


if __name__ == "__main__":
    unittest.main()
