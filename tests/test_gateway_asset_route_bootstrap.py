"""Tests for asset + peer route bootstrap factory."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
SRC_DIR = os.path.join(ROOT, "src")


def _load_modules():
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    def load(name, relpath, package=None):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = package or name.rsplit(".", 1)[0]
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_mod = load(f"{pkg}.state", "state.py")
    load(f"{pkg}.http.responses", os.path.join("http", "responses.py"), f"{pkg}.http")
    load(f"{pkg}.http.auth_gate", os.path.join("http", "auth_gate.py"), f"{pkg}.http")
    load(f"{pkg}.services.memory.types", os.path.join("services", "memory", "types.py"))
    load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    load(f"{pkg}.services.memory.context", os.path.join("services", "memory", "context.py"))
    query_mod = load(f"{pkg}.services.memory.query", os.path.join("services", "memory", "query.py"))
    load(f"{pkg}.services.memory.asset", os.path.join("services", "memory", "asset.py"))
    load(f"{pkg}.services.asset_gateway", os.path.join("services", "asset_gateway.py"))
    load(f"{pkg}.services.peer_mesh", os.path.join("services", "peer_mesh.py"))
    load(f"{pkg}.services.projection_register", os.path.join("services", "projection_register.py"))
    load(f"{pkg}.services.projection_ingest", os.path.join("services", "projection_ingest.py"))
    load(f"{pkg}.services.ingest", os.path.join("services", "ingest.py"))
    load(f"{pkg}.utils.multipart", os.path.join("utils", "multipart.py"))
    load(f"{pkg}.routes.ingest", os.path.join("routes", "ingest.py"))
    load(f"{pkg}.routes.asset", os.path.join("routes", "asset.py"))
    load(f"{pkg}.routes.peer", os.path.join("routes", "peer.py"))
    bootstrap_mod = load(
        f"{pkg}.services.asset_route_bootstrap",
        os.path.join("services", "asset_route_bootstrap.py"),
    )
    return state_mod, query_mod, bootstrap_mod


class AssetRouteBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.query_mod, cls.bootstrap_mod = _load_modules()

    def _hooks(self):
        m = sys.modules

        def noop(*a, **k):
            return None

        def empty(*a, **k):
            return {}

        return self.bootstrap_mod.AssetRouteBootstrapHooks(
            memory_asset=m["cnexus_gateway.services.memory.asset"].MemoryAssetHooks(
                load_federated_search_module=lambda: None,
                get_peer_registry=noop,
                get_dht_service=noop,
                get_identity_manager=noop,
                build_signed_headers=lambda *a, **k: {},
                blob_present=lambda _id: False,
                peer_pull_enabled=lambda: False,
                ensure_local=empty,
            ),
            asset_gateway=m["cnexus_gateway.services.asset_gateway"].AssetGatewayHooks(
                get_asset_processor=noop,
                get_vector_index=noop,
                get_clip_embedder=noop,
                get_asset_peer_sync=noop,
                get_asset_push_queue=noop,
                after_asset_indexed=noop,
                schedule_persist=noop,
                asset_peer_push_enabled=lambda: False,
            ),
            peer_mesh=m["cnexus_gateway.services.peer_mesh"].PeerMeshHooks(
                get_audit_log=noop,
                get_peer_registry=noop,
                get_gossip_sync=noop,
                get_genesis_sync=noop,
                get_p2p_handler=noop,
                get_negotiation_manager=noop,
                get_entropy_store=noop,
                get_connectivity_manager=noop,
                get_dht_service=noop,
                get_network_firewall=noop,
                header_lookup_peer=lambda _h: "",
                verify_audit_integrity=empty,
                identity_pubkey=lambda: "",
                audit_event=noop,
                perform_outbound_handshake=empty,
                local_peer_host=lambda: "127.0.0.1",
                get_catalog_service=noop,
                get_cognitive_service=noop,
                get_storage_service=noop,
                get_repair_service=noop,
                get_application_service=noop,
                memory_block_count=lambda: 0,
                trace_count=lambda: 0,
            ),
        )

    def test_build_wires_services_and_attaches_assets(self):
        engine = {"memory_store": type("MS", (), {"blocks": []})(), "trace": []}
        state = self.state_mod.EngineStateManager(engine)
        recall = self.query_mod.MemoryQueryService(
            state,
            self.query_mod.MemoryRecallHooks(get_cognitive_pruning_engine=lambda: None),
        )
        auth = type("Auth", (), {"check": lambda *a, **k: None})()
        ingest_routes = type("IngestRoutes", (), {"handle_post": lambda *a, **k: None})()
        projection = type("Proj", (), {"ingest_code": lambda *a, **k: {}, "ingest_image": lambda *a, **k: {}})()

        touched = []

        bundle = self.bootstrap_mod.build_asset_route_services(
            state,
            recall,
            auth,
            ingest_routes,
            projection,
            self._hooks(),
            touch_activity=lambda: touched.append(True),
        )

        self.assertIs(bundle.memory_asset, recall._assets)
        self.assertIsNotNone(bundle.asset_gateway)
        self.assertIsNotNone(bundle.peer_mesh)
        self.assertIs(bundle.asset_routes._assets, bundle.asset_gateway)
        self.assertIs(bundle.peer_routes._mesh, bundle.peer_mesh)


if __name__ == "__main__":
    unittest.main()
