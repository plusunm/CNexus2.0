"""Tests for network status service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_module():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    path = os.path.join(GATEWAY_DIR, "services", "network_status.py")
    spec = importlib.util.spec_from_file_location(f"{pkg}.services.network_status", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services"
    sys.modules[f"{pkg}.services.network_status"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _ServiceStub:
    def __init__(self, payload):
        self._payload = payload

    def status(self):
        return self._payload


class NetworkStatusServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_build_and_dht_status(self):
        service = self.mod.NetworkStatusService(
            self.mod.NetworkStatusHooks(
                get_connectivity_manager=lambda: _ServiceStub({"enabled": True}),
                get_dht_service=lambda: _ServiceStub({"enabled": True, "nodes": 1}),
                get_network_firewall=lambda: _ServiceStub({"enabled": False}),
            )
        )
        payload = service.build()
        self.assertTrue(payload["connectivity"]["enabled"])
        self.assertEqual(payload["dht"]["nodes"], 1)
        self.assertFalse(payload["firewall"]["enabled"])
        self.assertEqual(service.dht_status()["nodes"], 1)


if __name__ == "__main__":
    unittest.main()
