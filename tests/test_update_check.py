"""Tests for GitHub release update check."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_PATH = os.path.join(ROOT, "src", "core", "update_check.py")


def _load_mod():
    spec = importlib.util.spec_from_file_location("update_check", CORE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class UpdateCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_mod()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_normalize_and_compare_versions(self):
        self.assertEqual(self.mod.normalize_version("v2.4.0"), (2, 4, 0))
        self.assertEqual(self.mod.normalize_version("CNexus-2.10.1"), (2, 10, 1))
        self.assertEqual(self.mod.compare_versions("2.4.0", "2.5.0"), -1)
        self.assertEqual(self.mod.compare_versions("2.4.0", "2.4.0"), 0)
        self.assertEqual(self.mod.compare_versions("2.5.0", "2.4.0"), 1)
        self.assertEqual(self.mod.compare_versions("2.4.0", "2.4.1"), -1)

    def test_disabled_by_env(self):
        with patch.dict(os.environ, {"CNEXUS_UPDATE_CHECK": "0"}, clear=False):
            result = self.mod.check_update(self.data_dir, current_version="2.4.0")
        self.assertFalse(result.get("update_available"))
        self.assertFalse(result.get("enabled"))

    def test_update_available_from_github(self):
        remote = {
            "ok": True,
            "latest_version": "2.5.0",
            "tag_name": "v2.5.0",
            "release_name": "CNexus 2.5.0",
            "release_url": "https://github.com/plusunm/CNexus2.0/releases/tag/v2.5.0",
            "published_at": "2026-06-01T00:00:00Z",
            "release_notes": "Bug fixes",
        }
        with patch.object(self.mod, "fetch_github_latest", return_value=remote):
            result = self.mod.check_update(self.data_dir, current_version="2.4.0", force=True)
        self.assertTrue(result.get("update_available"))
        self.assertEqual(result.get("latest_version"), "2.5.0")
        cache = self.mod.load_cache(self.data_dir)
        self.assertEqual(cache.get("latest_version"), "2.5.0")

    def test_cache_reused_until_force(self):
        self.mod.save_cache(
            self.data_dir,
            {
                "checked_at": time.time(),
                "current_version": "2.4.0",
                "latest_version": "2.4.0",
                "update_available": False,
            },
        )
        with patch.object(self.mod, "fetch_github_latest") as fetch:
            result = self.mod.check_update(self.data_dir, current_version="2.4.0", force=False)
        fetch.assert_not_called()
        self.assertTrue(result.get("cached"))

        with patch.object(
            self.mod,
            "fetch_github_latest",
            return_value={
                "ok": True,
                "latest_version": "2.6.0",
                "tag_name": "v2.6.0",
                "release_name": "2.6.0",
                "release_url": "https://example.com",
                "published_at": None,
                "release_notes": "",
            },
        ) as fetch:
            forced = self.mod.check_update(self.data_dir, current_version="2.4.0", force=True)
        fetch.assert_called_once()
        self.assertTrue(forced.get("update_available"))

    def test_github_fetch_error_returns_stale_cache(self):
        self.mod.save_cache(
            self.data_dir,
            {
                "checked_at": self.mod.time.time() - 10,
                "current_version": "2.4.0",
                "latest_version": "2.5.0",
                "update_available": True,
                "release_url": "https://example.com/release",
            },
        )
        with patch.object(self.mod, "fetch_github_latest", return_value={"ok": False, "error": "offline"}):
            result = self.mod.check_update(self.data_dir, current_version="2.4.0", force=True)
        self.assertTrue(result.get("update_available"))
        self.assertTrue(result.get("stale"))


if __name__ == "__main__":
    unittest.main()
