"""Tests for anonymous install stats ping."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_PATH = os.path.join(ROOT, "src", "core", "install_stats.py")


def _load_mod():
    spec = importlib.util.spec_from_file_location("install_stats", CORE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class InstallStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_mod()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_install_id_created_once(self):
        a = self.mod.ensure_install_id(self.data_dir)
        b = self.mod.ensure_install_id(self.data_dir)
        self.assertEqual(a, b)
        self.assertTrue(os.path.isfile(self.mod.stats_file_path(self.data_dir)))

    def test_opt_in_requires_url_and_flag(self):
        record = {"opt_in": True}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CNEXUS_STATS_URL", None)
            os.environ.pop("CNEXUS_STATS_OPT_IN", None)
            self.assertFalse(self.mod.opt_in_enabled(record))
        with patch.dict(os.environ, {"CNEXUS_STATS_URL": "http://127.0.0.1:8787"}, clear=False):
            os.environ.pop("CNEXUS_STATS_OPT_IN", None)
            self.assertTrue(self.mod.opt_in_enabled(record))
            self.assertFalse(self.mod.opt_in_enabled({"opt_in": False}))

    def test_first_ping_only_once(self):
        with patch.dict(
            os.environ,
            {"CNEXUS_STATS_URL": "http://127.0.0.1:8787", "CNEXUS_STATS_OPT_IN": "1"},
            clear=False,
        ):
            with patch.object(self.mod, "send_install_ping", return_value={"ok": True, "status": 200}) as ping:
                first = self.mod.try_send_first_ping(self.data_dir, version="2.4.0", edition="personal")
                second = self.mod.try_send_first_ping(self.data_dir, version="2.4.0", edition="personal")
        self.assertTrue(first.get("sent"))
        self.assertEqual(ping.call_count, 1)
        self.assertEqual(second.get("skipped"), "already_sent")

    def test_payload_shape(self):
        payload = self.mod.build_payload(self.data_dir, version="2.4.0", edition="personal")
        self.assertEqual(payload["event"], "install")
        self.assertEqual(payload["version"], "2.4.0")
        self.assertEqual(payload["edition"], "personal")
        self.assertIn("install_id", payload)
        self.assertNotIn("pubkey", payload)


if __name__ == "__main__":
    unittest.main()
