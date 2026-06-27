"""Tests for discovered CNexus client merge + peers status API."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
NETWORK_DIR = os.path.join(ROOT, "src", "network")


def _load_discovered():
    path = os.path.join(NETWORK_DIR, "discovered_clients.py")
    spec = importlib.util.spec_from_file_location("discovered_clients", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_peers_service():
    pkg = "cnexus_gateway_disc"
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

    network_mod = load(f"{pkg}.services.network_status", "network_status.py")
    peers_mod = load(f"{pkg}.services.peers_status", "peers_status.py")
    return network_mod, peers_mod


class DiscoveredClientsMergeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_discovered()

    def test_merge_registry_dht_lan_excludes_local(self):
        rows = self.mod.merge_discovered_clients(
            local_pubkey="local-me",
            registry_peers={
                "peer-a": {"host": "http://192.168.1.10:7864", "status": "trusted", "last_seen": 100.0},
                "local-me": {"host": "http://127.0.0.1:7864", "status": "online"},
            },
            dht_nodes=[{"pubkey": "peer-b", "host": "http://192.168.1.11:7864", "last_seen": 200.0}],
            lan_rows=[{"pubkey": "peer-c", "host": "http://192.168.1.12:7864"}],
        )
        pubkeys = {row["pubkey"] for row in rows}
        self.assertEqual(pubkeys, {"peer-a", "peer-b", "peer-c"})
        by_pk = {row["pubkey"]: row for row in rows}
        self.assertTrue(by_pk["peer-a"]["trusted"])
        self.assertIn("registry", by_pk["peer-a"]["sources"])
        self.assertIn("dht", by_pk["peer-b"]["sources"])
        self.assertIn("lan", by_pk["peer-c"]["sources"])

    def test_merge_same_pubkey_unions_sources(self):
        rows = self.mod.merge_discovered_clients(
            registry_peers={"peer-x": {"host": "http://a", "status": "discovered"}},
            dht_nodes=[{"pubkey": "peer-x", "host": "http://b", "last_seen": time.time()}],
            lan_rows=[{"pubkey": "peer-x", "host": "http://c"}],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]["sources"]), {"registry", "dht", "lan"})


class PeersDiscoveredServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network_mod, cls.peers_mod = _load_peers_service()

    def test_build_discovered_without_refresh(self):
        class _Dht:
            def list_nodes(self):
                return [{"pubkey": "dht-1", "host": "http://10.0.0.2:7864", "last_seen": 1.0}]

        class _Registry:
            def get_all_peers(self):
                return {"reg-1": {"host": "http://10.0.0.3:7864", "status": "online", "last_seen": 2.0}}

            def get_peer(self, _pk):
                return None

            def save_peer(self, *_a, **_k):
                return {}

        network = self.network_mod.NetworkStatusService(
            self.network_mod.NetworkStatusHooks(
                get_connectivity_manager=lambda: None,
                get_dht_service=lambda: _Dht(),
                get_network_firewall=lambda: None,
            )
        )
        service = self.peers_mod.PeersStatusService(
            self.peers_mod.PeersStatusHooks(
                peer_registry_path=lambda: "/tmp/peers.json",
                get_peer_registry=lambda: _Registry(),
                get_gossip_sync=lambda: None,
                get_local_pubkey=lambda: "local-node",
            ),
            network,
        )
        payload = service.build_discovered(refresh=False)
        self.assertEqual(payload["count"], 2)
        self.assertFalse(payload["refreshed"])
        self.assertEqual(payload["online_count"], 1)


if __name__ == "__main__":
    unittest.main()
