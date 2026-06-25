"""Tests for peers status service."""

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

    network_mod = load(f"{pkg}.services.network_status", "network_status.py")
    peers_mod = load(f"{pkg}.services.peers_status", "peers_status.py")
    return network_mod, peers_mod


class _Registry:
    def get_all_peers(self):
        return {"pk1": {"host": "127.0.0.1:9000"}}


class _Gossip:
    def recent_results(self):
        return {"pk1": {"aligned": True}}


class _Connectivity:
    def status(self):
        return {"enabled": True}


class PeersStatusServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network_mod, cls.peers_mod = _load_modules()

    def test_build(self):
        network = self.network_mod.NetworkStatusService(
            self.network_mod.NetworkStatusHooks(
                get_connectivity_manager=lambda: _Connectivity(),
                get_dht_service=lambda: None,
                get_network_firewall=lambda: None,
            )
        )
        service = self.peers_mod.PeersStatusService(
            self.peers_mod.PeersStatusHooks(
                peer_registry_path=lambda: "/tmp/peers.json",
                get_peer_registry=lambda: _Registry(),
                get_gossip_sync=lambda: _Gossip(),
            ),
            network,
        )
        status = service.build()
        self.assertEqual(status["peer_count"], 1)
        self.assertIn("pk1", status["peers"])
        self.assertTrue(status["gossip_recent"]["pk1"]["aligned"])
        self.assertTrue(status["network"]["connectivity"]["enabled"])


if __name__ == "__main__":
    unittest.main()
