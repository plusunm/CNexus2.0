"""Tests for resilience status service."""

from __future__ import annotations

import importlib.util
import os
import sys
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

    def load(name, filename):
        path = os.path.join(GATEWAY_DIR, "services", filename)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = f"{pkg}.services"
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    audit_mod = load(f"{pkg}.services.audit_chain_status", "audit_chain_status.py")
    resilience_mod = load(f"{pkg}.services.resilience_status", "resilience_status.py")
    metrics_spec = importlib.util.spec_from_file_location("metrics", os.path.join(API_DIR, "metrics.py"))
    metrics_mod = importlib.util.module_from_spec(metrics_spec)
    assert metrics_spec.loader is not None
    metrics_spec.loader.exec_module(metrics_mod)
    return audit_mod, resilience_mod, metrics_mod


class _Gossip:
    def recent_results(self):
        return {}

    def heartbeat_results(self):
        return {}


class _AuditStub:
    def build(self):
        return {"integrity": {"ok": True}}


class ResilienceStatusServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_mod, cls.resilience_mod, cls.metrics_mod = _load_modules()

    def _audit_service(self):
        return self.audit_mod.AuditChainStatusService(
            self.audit_mod.AuditChainStatusHooks(
                audit_optional=False,
                audit_log_path=lambda: "/tmp/audit.log",
                get_audit_log=lambda: None,
                get_audit_integrity=lambda: {"ok": True},
            )
        )

    def test_solo_when_metrics_unavailable(self):
        service = self.resilience_mod.ResilienceStatusService(
            self.resilience_mod.ResilienceStatusHooks(
                get_metrics_module=lambda: False,
                get_gossip_sync=lambda: object(),
                get_peer_registry=lambda: None,
                heartbeat_stale_seconds=lambda: 120.0,
            ),
            self._audit_service(),
        )
        self.assertEqual(service.build()["label"], "solo")

    def test_build_with_metrics(self):
        gossip = _Gossip()
        service = self.resilience_mod.ResilienceStatusService(
            self.resilience_mod.ResilienceStatusHooks(
                get_metrics_module=lambda: self.metrics_mod,
                get_gossip_sync=lambda: gossip,
                get_peer_registry=lambda: None,
                heartbeat_stale_seconds=lambda: 120.0,
            ),
            self._audit_service(),
        )
        payload = service.build()
        self.assertIn("score", payload)
        self.assertIn("label", payload)


if __name__ == "__main__":
    unittest.main()
