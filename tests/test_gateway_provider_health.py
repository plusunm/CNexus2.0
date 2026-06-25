"""Provider health gate tests."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load():
    path = os.path.join(GATEWAY_DIR, "services", "provider_health.py")
    spec = importlib.util.spec_from_file_location("cnexus_gateway.services.provider_health", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "cnexus_gateway.services"
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ProviderHealthGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_failure_blocks_until_cooldown(self):
        gate = self.mod.ProviderHealthGate(cooldown_seconds=0.2)
        row = {"id": "deepseek-chat", "provider": "openai_compatible"}
        self.assertTrue(gate.allow(row))
        gate.record_failure(row)
        self.assertFalse(gate.allow(row))
        time.sleep(0.25)
        self.assertTrue(gate.allow(row))

    def test_success_clears_failure(self):
        gate = self.mod.ProviderHealthGate(cooldown_seconds=30)
        row = {"id": "ollama-local", "provider": "ollama"}
        gate.record_failure(row)
        self.assertFalse(gate.allow(row))
        gate.record_success(row)
        self.assertTrue(gate.allow(row))


if __name__ == "__main__":
    unittest.main()
