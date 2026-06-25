"""Tests for L0 fragment status services."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load(name, filename):
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    path = os.path.join(GATEWAY_DIR, "services", filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services"
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class L0FragmentServicesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity_mod = _load("cnexus_gateway.services.identity_status", "identity_status.py")
        cls.audit_mod = _load("cnexus_gateway.services.audit_chain_status", "audit_chain_status.py")
        cls.api_auth_mod = _load("cnexus_gateway.services.api_auth_status", "api_auth_status.py")
        cls.consensus_mod = _load("cnexus_gateway.services.consensus_status", "consensus_status.py")
        cls.assets_mod = _load("cnexus_gateway.services.assets_status", "assets_status.py")

    def test_identity_loaded(self):
        im = type("IM", (), {"public_key_hex": lambda self: "abc"})()
        status = self.identity_mod.IdentityStatusService(
            self.identity_mod.IdentityStatusHooks(
                identity_optional=False,
                identity_key_path=lambda: "/id",
                get_identity_manager=lambda: im,
            )
        ).build()
        self.assertEqual(status["pubkey"], "abc")

    def test_api_auth_disabled(self):
        self.assertFalse(
            self.api_auth_mod.ApiAuthStatusService(
                self.api_auth_mod.ApiAuthStatusHooks(get_auth_middleware=lambda: None)
            ).build()["enabled"]
        )

    def test_assets_local_count(self):
        proc = type("P", (), {"list_assets": lambda self, limit=500: [1, 2]})()
        status = self.assets_mod.AssetsStatusService(
            self.assets_mod.AssetsStatusHooks(
                asset_embed_enabled=lambda: True,
                clip_enabled=lambda: False,
                asset_peer_push_enabled=lambda: True,
                asset_peer_pull_enabled=lambda: False,
                get_asset_vector_index=lambda: None,
                get_asset_peer_sync=lambda: None,
                get_asset_push_queue=lambda: None,
                get_asset_processor=lambda: proc,
            )
        ).build()
        self.assertEqual(status["local_assets"], 2)


if __name__ == "__main__":
    unittest.main()
