"""L3 project binding + L1 conversation scratch tests."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from gateway.services.conversation_scratch import (  # noqa: E402
    append_scratch_turn,
    default_scratch_state,
    format_scratch_for_prompt,
)
from gateway.services.memory.project import (  # noqa: E402
    attach_project_scope,
    block_visible_for_active_project,
    default_active_project,
    normalize_active_project,
    spec_visible_for_active_project,
    stamp_block_protection,
)


class ProjectBindingTests(unittest.TestCase):
    def test_unlocked_project_does_not_filter(self):
        block = stamp_block_protection(
            {
                "block_id": "p-other",
                "data": {"content": "other", "project_id": "alpha"},
            },
            "project",
        )
        active = normalize_active_project({"project_id": "beta", "locked": False})
        self.assertTrue(block_visible_for_active_project(block, active))

    def test_locked_project_filters_l3(self):
        block = stamp_block_protection(
            {
                "block_id": "p-alpha",
                "data": {"content": "alpha", "project_id": "alpha"},
            },
            "project",
        )
        other = stamp_block_protection(
            {
                "block_id": "p-beta",
                "data": {"content": "beta", "project_id": "beta"},
            },
            "project",
        )
        active = normalize_active_project({"project_id": "alpha", "locked": True})
        self.assertTrue(block_visible_for_active_project(block, active))
        self.assertFalse(block_visible_for_active_project(other, active))

    def test_foundation_always_visible_when_locked(self):
        block = stamp_block_protection(
            {
                "block_id": "f-1",
                "data": {"content": "constitution", "project_id": "other"},
            },
            "foundation",
        )
        active = normalize_active_project({"project_id": "alpha", "locked": True})
        self.assertTrue(block_visible_for_active_project(block, active))

    def test_attach_project_scope_without_level_change(self):
        block = stamp_block_protection({"block_id": "m-1", "data": {"content": "x"}}, "long_term")
        scoped = attach_project_scope(block, project_id="my-project")
        self.assertEqual(scoped["data"]["project_id"], "my-project")
        self.assertEqual(scoped["data"]["memory_level"], "long_term")

    def test_spec_visibility_matches_block(self):
        spec = {"id": "n1", "memory_level": "project", "project_id": "alpha"}
        active = normalize_active_project({"project_id": "beta", "locked": True})
        self.assertFalse(spec_visible_for_active_project(spec, active))


class ConversationScratchTests(unittest.TestCase):
    def test_append_and_format_scratch(self):
        engine = {"conversation_scratch": default_scratch_state()}

        def mutate(fn):
            fn(engine)
            return engine["conversation_scratch"]

        append_scratch_turn(
            mutate,
            session_id="sess-1",
            user_text="hello",
            assistant_text="world",
            trace_id="t-1",
        )
        text = format_scratch_for_prompt(engine["conversation_scratch"])
        self.assertIn("Conversation Scratch", text)
        self.assertIn("hello", text)
        self.assertIn("world", text)


if __name__ == "__main__":
    unittest.main()
