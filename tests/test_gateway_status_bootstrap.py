"""Tests for status bootstrap factory."""

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
    activation_mod = load(f"{pkg}.services.activation", os.path.join("services", "activation.py"))
    load(f"{pkg}.services.converse_speech", os.path.join("services", "converse_speech.py"))
    for fname in (
        "consolidation_status.py",
        "replay_status.py",
        "awakening_status.py",
        "pruning_status.py",
        "entropy_status.py",
        "persistence_status.py",
        "negotiation_conflict_status.py",
        "reflection_status.py",
        "conflict_resolution_status.py",
        "status_subsystems.py",
        "network_status.py",
        "identity_status.py",
        "audit_chain_status.py",
        "api_auth_status.py",
        "consensus_status.py",
        "assets_status.py",
        "resilience_status.py",
        "peers_status.py",
        "dashboard_status.py",
        "status_snapshot.py",
        "shadow_projection.py",
    ):
        load(f"{pkg}.services.{fname[:-3]}", os.path.join("services", fname))

    bootstrap_mod = load(f"{pkg}.services.status_bootstrap", os.path.join("services", "status_bootstrap.py"))
    return state_mod, activation_mod, bootstrap_mod


class StatusBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.activation_mod, cls.bootstrap_mod = _load_modules()

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.persist_path = os.path.join(self._tmpdir.name, "state.json")
        with open(self.persist_path, "w", encoding="utf-8") as f:
            f.write("{}")
        self.engine = {
            "memory_store": type("MS", (), {"blocks": [{"label": "semantic"}]})(),
            "trace": [],
            "projection": {"nodes": {}, "links": []},
            "consolidation": {"last_shallow_at": 1.0},
            "negotiation_conflicts": [],
            "state": type("State", (), {"goal": {"current": "x", "progress": 0.0}})(),
        }

    def tearDown(self):
        self._tmpdir.cleanup()

    def _hooks(self):
        m = sys.modules
        return self.bootstrap_mod.StatusBootstrapHooks(
            consolidation=m["cnexus_gateway.services.consolidation_status"].ConsolidationStatusHooks(
                rem_consolidation_status=lambda c, ctx: {"enabled": True},
                build_rem_context=lambda: {"specs": []},
            ),
            replay=m["cnexus_gateway.services.replay_status"].ReplayStatusHooks(
                get_log_replay_engine=lambda: None,
                get_audit_log=lambda: None,
                get_state_reconstructor=lambda: None,
            ),
            awakening=m["cnexus_gateway.services.awakening_status"].AwakeningStatusHooks(
                read_awakening_base=lambda: {"phase": "idle", "label": "idle", "progress": 0.0, "alive": True},
                genesis_status=lambda: {"enabled": False},
                reconstructor_status=lambda: {},
            ),
            pruning=m["cnexus_gateway.services.pruning_status"].PruningStatusHooks(
                get_cognitive_pruning_engine=lambda: None,
            ),
            entropy=m["cnexus_gateway.services.entropy_status"].EntropyStatusHooks(
                get_entropy_store=lambda: False,
                get_peer_registry=lambda: None,
            ),
            persistence=m["cnexus_gateway.services.persistence_status"].PersistenceStatusHooks(
                persist_version="test-v1",
                persist_file_path=lambda: self.persist_path,
                persist_meta=lambda: {"saved_at": 1.0, "loaded_at": 2.0},
            ),
            negotiation_conflict=m["cnexus_gateway.services.negotiation_conflict_status"].NegotiationConflictStatusHooks(
                negotiation_conflict_enabled=lambda: False,
                negotiation_conflict_use_llm=lambda: False,
                negotiation_conflict_context=lambda: "",
            ),
            reflection=m["cnexus_gateway.services.reflection_status"].ReflectionStatusHooks(
                reflection_engine_status=lambda: {"enabled": False},
            ),
            conflict_resolution=m["cnexus_gateway.services.conflict_resolution_status"].ConflictResolutionStatusHooks(
                conflict_agent_status=lambda: {"enabled": False},
                negotiation_conflict_enabled=lambda: False,
                negotiation_conflict_use_llm=lambda: False,
            ),
            network=m["cnexus_gateway.services.network_status"].NetworkStatusHooks(
                get_connectivity_manager=lambda: None,
                get_dht_service=lambda: None,
                get_network_firewall=lambda: None,
            ),
            identity=m["cnexus_gateway.services.identity_status"].IdentityStatusHooks(
                identity_optional=lambda: True,
                identity_key_path=lambda: "",
                get_identity_manager=lambda: None,
            ),
            audit_chain=m["cnexus_gateway.services.audit_chain_status"].AuditChainStatusHooks(
                audit_optional=lambda: True,
                audit_log_path=lambda: "",
                get_audit_log=lambda: None,
                get_audit_integrity=lambda: {"ok": True},
            ),
            api_auth=m["cnexus_gateway.services.api_auth_status"].ApiAuthStatusHooks(
                get_auth_middleware=lambda: None,
            ),
            consensus=m["cnexus_gateway.services.consensus_status"].ConsensusStatusHooks(
                get_negotiation_manager=lambda: None,
                get_reputation_registry=lambda: None,
            ),
            assets=m["cnexus_gateway.services.assets_status"].AssetsStatusHooks(
                asset_embed_enabled=lambda: False,
                clip_enabled=lambda: False,
                asset_peer_push_enabled=lambda: False,
                asset_peer_pull_enabled=lambda: False,
                get_asset_vector_index=lambda: None,
                get_asset_peer_sync=lambda: None,
                get_asset_push_queue=lambda: None,
                get_asset_processor=lambda: None,
            ),
            resilience=m["cnexus_gateway.services.resilience_status"].ResilienceStatusHooks(
                get_metrics_module=lambda: None,
                get_gossip_sync=lambda: None,
                get_peer_registry=lambda: None,
                heartbeat_stale_seconds=lambda: 60.0,
            ),
            peers=m["cnexus_gateway.services.peers_status"].PeersStatusHooks(
                peer_registry_path=lambda: "",
                get_peer_registry=lambda: None,
                get_gossip_sync=lambda: None,
            ),
            dashboard=m["cnexus_gateway.services.dashboard_status"].DashboardStatusHooks(
                get_metrics_module=lambda: None,
                get_audit_log=lambda: None,
                get_gossip_sync=lambda: None,
                get_peer_registry=lambda: None,
                heartbeat_stale_seconds=lambda: 60.0,
                server_port=7864,
            ),
            shadow=m["cnexus_gateway.services.shadow_projection"].ShadowProjectionHooks(
                find_ollama_binary=lambda: None,
                probe_ollama=lambda: False,
                ollama_host="http://127.0.0.1:11434",
                active_chat_model_id=lambda: None,
            ),
        )

    def test_build_status_services_wires_subsystems_and_snapshot(self):
        state = self.state_mod.EngineStateManager(self.engine)
        activation = self.activation_mod.ActivationService(
            state,
            self.activation_mod.ActivationHooks(collect_node_specs=lambda: []),
            default_threshold=0.4,
            default_inject_limit=5,
        )
        bundle = self.bootstrap_mod.build_status_services(state, activation, self._hooks())

        self.assertTrue(bundle.subsystems.persistence_status()["exists"])
        self.assertIsNotNone(bundle.snapshot)
        self.assertIsNotNone(bundle.dashboard)
        self.assertIsNotNone(bundle.shadow)
        self.assertEqual(bundle.subsystems.consolidation_status()["last_shallow_at"], 1.0)


if __name__ == "__main__":
    unittest.main()
