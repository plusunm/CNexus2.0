"""Smoke script structure tests — no live LAN required."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lan_dual_node_smoke.py"


def _load_smoke():
    spec = importlib.util.spec_from_file_location("lan_dual_node_smoke", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class LanDualNodeSmokeTests(unittest.TestCase):
    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file())

    def test_main_fails_without_connect_ok(self):
        smoke = _load_smoke()

        def fake_request(method, url, body=None, *, timeout=20.0):
            if url.endswith("/api/connectivity/identity"):
                return 200, {"ok": True, "pubkey": "aa" * 32}
            if url.endswith("/api/application/status"):
                return 200, {"ok": True, "control": {"phase": "idle"}}
            if url.endswith("/api/connectivity/connect"):
                return 502, {"ok": False, "error": "no_viable_path"}
            return 404, {"ok": False}

        argv = ["lan_dual_node_smoke.py", "--peer-id", "bb" * 32]
        with patch.object(sys, "argv", argv):
            with patch.object(smoke, "_request", side_effect=fake_request):
                code = smoke.main()
        self.assertEqual(code, 1)

    def test_main_passes_happy_path_without_repair(self):
        smoke = _load_smoke()
        peer = "bb" * 32

        def fake_request(method, url, body=None, *, timeout=20.0):
            if url.endswith("/api/connectivity/identity"):
                return 200, {"ok": True, "pubkey": "aa" * 32}
            if url.endswith("/api/application/status"):
                return 200, {"ok": True, "control": {"phase": "idle"}}
            if url.endswith("/api/connectivity/connect"):
                return 200, {
                    "ok": True,
                    "url": "http://192.168.1.2:7864",
                    "repair_hook": {
                        "ok": True,
                        "executed": False,
                        "missing_count": 0,
                        "repair_plans": [],
                    },
                    "application": {"ok": True, "phase": "connected"},
                }
            if url.endswith("/api/application/diagnose"):
                return 200, {"ok": True, "diff": {"missing_total": 0}, "plan_count": 0}
            return 404, {"ok": False}

        argv = ["lan_dual_node_smoke.py", "--peer-id", peer]
        with patch.object(sys, "argv", argv):
            with patch.object(smoke, "_request", side_effect=fake_request):
                code = smoke.main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
