"""Tests for converse mode configuration service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
GATEWAY_DIR = os.path.join(SRC, "gateway")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load_config_module():
    pkg = "cnexus_gateway.services"
    for name, fname in (
        ("converse_thinking", "converse_thinking.py"),
        ("converse_config", "converse_config.py"),
    ):
        path = os.path.join(GATEWAY_DIR, "services", fname)
        spec = importlib.util.spec_from_file_location(f"{pkg}.{name}", path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg
        sys.modules[spec.name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    return sys.modules[f"{pkg}.converse_config"]


class ConverseConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_mod = _load_config_module()

    def _service(self):
        return self.config_mod.ConverseConfigService(
            activation_threshold=0.4,
            inject_limit=2,
            inject_desc_max=80,
            llm_max_tokens=1024,
            converse_modes=frozenset({"fast", "deep", "raw"}),
            hooks=self.config_mod.ConverseConfigHooks(
                global_entropy_int=lambda: 99,
            ),
        )

    def test_normalize_converse_mode_aliases(self):
        svc = self._service()
        self.assertEqual(svc.normalize_converse_mode("long_context"), "deep")
        self.assertEqual(svc.normalize_converse_mode("user-only"), "raw")
        self.assertEqual(svc.normalize_converse_mode("unknown"), "fast")

    def test_fast_profile(self):
        svc = self._service()
        profile = svc.converse_mode_profile("fast")
        self.assertEqual(profile["mode"], "fast")
        self.assertTrue(profile["inject_memory"])
        self.assertEqual(profile["llm_max_tokens"], 1024)

    def test_thinking_mode_aliases(self):
        svc = self._service()
        self.assertEqual(svc.normalize_thinking_mode("creative"), "emergent")
        self.assertEqual(svc.normalize_thinking_mode("strict"), "precision")

    def test_thinking_fallback(self):
        svc = self._service()
        params = svc.thinking_inference_params("emergent")
        self.assertEqual(params["thinking_mode"], "emergent")
        self.assertEqual(params["global_entropy_int"], 99)

    def test_parse_request_modes(self):
        svc = self._service()
        converse_mode, thinking_mode = svc.parse_request_modes(
            {"mode": "emergent", "converse_mode": "deep"}
        )
        self.assertEqual(converse_mode, "deep")
        self.assertEqual(thinking_mode, "emergent")


if __name__ == "__main__":
    unittest.main()
