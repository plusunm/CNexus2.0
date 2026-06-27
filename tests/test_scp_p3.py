"""SCP P3 — expert distill plugin, ingest tagging, fact-confirm gate."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from gateway.services.ingest import _expert_meta_from_policy
from kernel.block_store import BlockStore
from plugins.expert_distill.distill import ExpertDistillEngine
from plugins.expert_distill.service import ExpertDistillService, fact_confirm_block
from plugins.expert_distill.tagging import stamp_expert_metadata
from semantic.anti_loop import should_skip_rem_for_block


class IngestExpertMetaTests(unittest.TestCase):
    def test_policy_subject_id(self):
        meta = _expert_meta_from_policy({"subject_id": "expert:alice", "semantic_dimension": "style"})
        self.assertEqual(meta["subject_id"], "expert:alice")
        self.assertEqual(meta["semantic_dimension"], "style")

    def test_filename_expert_prefix(self):
        meta = _expert_meta_from_policy({}, filename="expert:bob/notes.md")
        self.assertEqual(meta["subject_id"], "bob")

    def test_no_subject_returns_none(self):
        self.assertIsNone(_expert_meta_from_policy({}, filename="notes.md"))


class ExpertDistillServiceTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("CNEXUS_EXPERT_DISTILL")
        os.environ["CNEXUS_EXPERT_DISTILL"] = "1"
        self.store = BlockStore()

        def mutate_store(apply):
            return apply(self.store)

        self.svc = ExpertDistillService(
            mutate_store,
            lambda: list(self.store.blocks),
            distill_engine=ExpertDistillEngine(),
        )

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("CNEXUS_EXPERT_DISTILL", None)
        else:
            os.environ["CNEXUS_EXPERT_DISTILL"] = self._prev

    def _seed_corpus(self, subject: str = "expert:alice"):
        self.store.add(
            stamp_expert_metadata(
                {
                    "label": "semantic",
                    "block_id": "src-1",
                    "data": {"content": "Alice always validates assumptions before committing to architecture."},
                    "importance": 0.7,
                },
                subject_id=subject,
                semantic_dimension="fact",
            )
        )
        self.store.add(
            stamp_expert_metadata(
                {
                    "label": "narrative",
                    "block_id": "src-2",
                    "data": {"content": "Alice writes in concise analytical paragraphs with numbered lists."},
                    "importance": 0.6,
                },
                subject_id=subject,
                semantic_dimension="style",
            )
        )

    def test_list_subjects(self):
        self._seed_corpus()
        subjects = self.svc.list_subjects()
        self.assertEqual(len(subjects), 1)
        self.assertEqual(subjects[0]["subject_id"], "expert:alice")
        self.assertGreaterEqual(subjects[0]["block_count"], 2)

    def test_capture_for_subject(self):
        result = self.svc.capture_for_subject(
            subject_id="expert:carol",
            content="Carol prefers risk-adjusted tradeoffs.",
            semantic_dimension="decision",
        )
        self.assertTrue(result["ok"])
        block = self.store.blocks[-1]
        self.assertEqual(block["data"]["subject_id"], "expert:carol")
        self.assertEqual(block["data"]["semantic_dimension"], "decision")

    def test_run_distill_writes_blocks(self):
        self._seed_corpus()
        result = self.svc.run_distill(subject_id="expert:alice", modes=["fact", "style"])
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["blocks_written"], 2)
        dims = {b["data"].get("semantic_dimension") for b in self.store.blocks if b["block_id"].startswith("expert-")}
        self.assertIn("fact", dims)
        self.assertIn("style", dims)

    def test_fact_confirm_promotes_block(self):
        pending = stamp_expert_metadata(
            {
                "label": "semantic",
                "block_id": "pending-fact",
                "data": {"content": "Distilled fact pending review."},
                "importance": 0.7,
            },
            subject_id="expert:alice",
            semantic_dimension="fact",
        )
        pending["data"]["fact_confirm_required"] = True
        self.store.add(pending)
        result = self.svc.confirm_fact("pending-fact")
        self.assertTrue(result["ok"])
        confirmed = next(b for b in self.store.blocks if b["block_id"] == "pending-fact")
        self.assertTrue(confirmed["data"].get("fact_confirmed"))
        self.assertFalse(should_skip_rem_for_block(confirmed))

    def test_fact_confirm_block_helper(self):
        promoted = fact_confirm_block(
            {
                "block_id": "x",
                "data": {"derived_from_expert_session": True, "fact_confirm_required": True},
                "importance": 0.5,
            }
        )
        self.assertTrue(promoted["data"]["fact_confirmed"])
        self.assertEqual(promoted["data"]["provenance"], "local-full")


if __name__ == "__main__":
    unittest.main()
