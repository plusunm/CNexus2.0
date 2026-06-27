"""Boot share policy tests."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from application.share_boot import bootstrap_share_local_memory  # noqa: E402

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

    def test_skips_when_already_published(self):
        app = MagicMock()
        app.cognitive.store.get_head_commit_id.return_value = "cc" * 32
        blocks = [{"block_id": "b1", "data": {"content": "hello"}}]
        report = bootstrap_share_local_memory(app, memory_blocks=blocks, identity_pubkey=OWNER)
        self.assertTrue(report["skipped"])
        self.assertEqual(report["reason"], "already_published")
        app.publish_memory.assert_not_called()

    def test_respects_disabled_env(self):
        os.environ["CNEXUS_SHARE_LOCAL_MEMORY"] = "0"
        try:
            app = MagicMock()
            blocks = [{"block_id": "b1", "data": {"content": "hello"}}]
            report = bootstrap_share_local_memory(app, memory_blocks=blocks, identity_pubkey=OWNER)
            self.assertEqual(report["reason"], "disabled")
        finally:
            os.environ.pop("CNEXUS_SHARE_LOCAL_MEMORY", None)


if __name__ == "__main__":
    unittest.main()
