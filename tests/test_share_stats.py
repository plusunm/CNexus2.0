"""Share stats + boot policy tests."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from application.share_boot import bootstrap_share_local_memory  # noqa: E402
from core.share_stats import (  # noqa: E402
    load_share_record,
    record_local_share,
    share_stats_enabled,
    try_register_share,
)

OWNER = "aa" * 32


class ShareBootTests(unittest.TestCase):
    def test_skips_when_no_blocks(self):
        app = MagicMock()
        report = bootstrap_share_local_memory(app, memory_blocks=[], identity_pubkey=OWNER)
        self.assertTrue(report["skipped"])
        self.assertEqual(report["reason"], "no_blocks")
        app.publish_memory.assert_not_called()

    def test_publishes_when_no_head(self):
        app = MagicMock()
        app.cognitive.store.get_head_commit_id.return_value = ""
        app.publish_memory.return_value = {
            "ok": True,
            "graph_id": "g1",
            "commit_id": "c1",
            "root_hash": "r1",
        }
        blocks = [{"block_id": "b1", "data": {"content": "hello"}}]
        report = bootstrap_share_local_memory(app, memory_blocks=blocks, identity_pubkey=OWNER)
        self.assertTrue(report.get("shared"))
        app.publish_memory.assert_called_once()

    def test_skips_when_already_published_unless_always(self):
        os.environ["CNEXUS_SHARE_LOCAL_MEMORY_ALWAYS"] = "0"
        try:
            app = MagicMock()
            app.cognitive.store.get_head_commit_id.return_value = "cc" * 32
            blocks = [{"block_id": "b1", "data": {"content": "hello"}}]
            report = bootstrap_share_local_memory(app, memory_blocks=blocks, identity_pubkey=OWNER)
            self.assertTrue(report["skipped"])
            self.assertEqual(report["reason"], "already_published")
            app.publish_memory.assert_not_called()
        finally:
            os.environ.pop("CNEXUS_SHARE_LOCAL_MEMORY_ALWAYS", None)

    def test_republishes_by_default_when_already_published(self):
        app = MagicMock()
        app.cognitive.store.get_head_commit_id.return_value = "cc" * 32
        app.publish_memory.return_value = {
            "ok": True,
            "graph_id": "g1",
            "commit_id": "c2",
            "root_hash": "r2",
        }
        blocks = [{"block_id": "b1", "data": {"content": "hello"}}]
        report = bootstrap_share_local_memory(app, memory_blocks=blocks, identity_pubkey=OWNER)
        self.assertTrue(report.get("shared"))
        app.publish_memory.assert_called_once()

    def test_respects_disabled_env(self):
        os.environ["CNEXUS_SHARE_LOCAL_MEMORY"] = "0"
        try:
            app = MagicMock()
            blocks = [{"block_id": "b1", "data": {"content": "hello"}}]
            report = bootstrap_share_local_memory(app, memory_blocks=blocks, identity_pubkey=OWNER)
            self.assertEqual(report["reason"], "disabled")
        finally:
            os.environ.pop("CNEXUS_SHARE_LOCAL_MEMORY", None)


class ShareStatsTests(unittest.TestCase):
    def test_record_local_share(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = record_local_share(tmp, graph_id="g1", block_count=3)
            self.assertEqual(record["graph_id"], "g1")
            self.assertEqual(record["block_count"], 3)
            self.assertEqual(record["share_count"], 1)
            again = record_local_share(tmp, graph_id="g1", block_count=5)
            self.assertEqual(again["share_count"], 2)
            loaded = load_share_record(tmp)
            self.assertEqual(loaded["block_count"], 5)

    def test_try_register_share_skips_without_stats_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ.pop("CNEXUS_STATS_URL", None)
            result = try_register_share(tmp, graph_id="g1", block_count=1)
            self.assertTrue(result.get("ok"))
            self.assertEqual(result.get("skipped"), "stats_url_unconfigured")

    @patch("core.share_stats.send_share_ping")
    def test_try_register_share_pings_when_configured(self, mock_ping):
        mock_ping.return_value = {"ok": True, "status": 200, "response": {}}
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["CNEXUS_STATS_URL"] = "http://stats.test"
            try:
                self.assertTrue(share_stats_enabled())
                result = try_register_share(tmp, graph_id="g1", block_count=2)
                self.assertTrue(result.get("ok"))
                mock_ping.assert_called_once()
                payload = mock_ping.call_args[0][1]
                self.assertEqual(payload["event"], "share")
                self.assertEqual(payload["graph_id"], "g1")
                self.assertEqual(payload["block_count"], 2)
            finally:
                os.environ.pop("CNEXUS_STATS_URL", None)


if __name__ == "__main__":
    unittest.main()
