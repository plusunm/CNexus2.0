"""Tests for converse thinking helpers."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_module():
    path = os.path.join(GATEWAY_DIR, "services", "converse_thinking.py")
    spec = importlib.util.spec_from_file_location("cnexus_gateway.services.converse_thinking", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "cnexus_gateway.services"
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ConverseThinkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_emergent_inference_params(self):
        params = self.mod.thinking_inference_params("emergent", 123)
        self.assertEqual(params["thinking_mode"], "emergent")
        self.assertTrue(params["use_reflection"])
        self.assertFalse(params["provenance_enforced"])

    def test_precision_system_content(self):
        text = self.mod.build_precision_system_content("mem", provenance_preamble="P:")
        self.assertIn("P:", text)
        self.assertIn("mem", text)


if __name__ == "__main__":
    unittest.main()
