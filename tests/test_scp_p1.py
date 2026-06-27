"""SCP P1 — composer slots, provenance gate, anti-loop, status."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from kernel.block_store import BlockStore
from semantic.anti_loop import apply_antiloop_after_store, should_skip_rem_for_block
from semantic.composer import ContextComposer
from semantic.provenance_gate import ProvenanceGate, is_authoritative
from semantic.scp import SemanticControlPlane
from semantic.types import (
    ArbitrationDecision,
    PromptPlan,
    RecallPlan,
    SCPRequest,
    SemanticCandidate,
    TurnProfile,
)


class ComposerSlotTests(unittest.TestCase):
    def test_slot_isolation_with_expert_layers(self):
        composer = ContextComposer()
        request = SCPRequest(
            query="q",
            turn_profile=TurnProfile(style_source="prompt", expert_mode="expert:test"),
            activation_context="OS memory layer",
            prompt_candidates=[
                SemanticCandidate(block_id="p1", dimension="procedure", content="Prioritize facts.", source="prompt"),
                SemanticCandidate(block_id="p2", dimension="style", content="Formal tone.", source="prompt"),
            ],
            recall_candidates=[
                SemanticCandidate(block_id="r1", dimension="fact", content="User prefers concise answers.", source="recall"),
                SemanticCandidate(block_id="r2", dimension="style", content="should be excluded", source="recall"),
            ],
        )
        decision = SemanticArbitrationLayerStub().arbitrate(request)
        composed = composer.compose(request, decision)
        self.assertIn("Expert Procedure", composed)
        self.assertIn("Expert Style (not fact)", composed)
        self.assertIn("Memory Evidence", composed)
        self.assertIn("OS memory layer", composed)
        self.assertNotIn("should be excluded", composed)

    def test_no_expert_candidates_returns_os_layer_only(self):
        composer = ContextComposer()
        request = SCPRequest(
            query="q",
            turn_profile=TurnProfile(),
            activation_context="only os",
        )
        decision = ArbitrationDecision()
        self.assertEqual(composer.compose(request, decision), "only os")


class ProvenanceGateTests(unittest.TestCase):
    def test_persona_synthetic_not_authoritative(self):
        self.assertFalse(is_authoritative("persona-synthetic"))
        gate = ProvenanceGate()
        text = gate.format_candidate(
            SemanticCandidate(dimension="style", content="Be concise."),
            profile=TurnProfile(),
        )
        self.assertIn("not fact", text)


class AntiLoopTests(unittest.TestCase):
    def test_tags_expert_session_episodic(self):
        bs = BlockStore()
        bs.add(
            {
                "label": "episodic",
                "block_id": "ep:1",
                "data": {"response_text": "expert styled reply"},
            }
        )
        meta = {"expert_mode": "expert:alice"}
        iteration_meta = {}
        report = apply_antiloop_after_store(bs, meta, iteration_meta)
        self.assertTrue(report["tagged"])
        self.assertTrue(iteration_meta.get("expert_session"))
        block = bs.blocks[-1]
        self.assertTrue(block["data"].get("derived_from_expert_session"))
        self.assertTrue(should_skip_rem_for_block(block))


class SCPIntegrationTests(unittest.TestCase):
    def test_admit_with_expert_candidates_includes_preamble(self):
        scp = SemanticControlPlane(persist=False)

        def compose(mem: str = "") -> str:
            return f"LLM::{mem}"

        request = SCPRequest(
            query="hello",
            turn_profile=TurnProfile(expert_mode="expert:bob", style_source="prompt"),
            activation_context="base memory",
            prompt_candidates=[
                SemanticCandidate(block_id="p1", dimension="style", content="Analytical tone.", source="prompt"),
            ],
            compose_llm_context=compose,
        )
        response = scp.admit(request)
        self.assertTrue(response.admitted)
        self.assertIn("NOT factual sources", response.llm_context)
        self.assertIn("Expert Style", response.llm_context)


class SemanticArbitrationLayerStub:
    """Minimal SAL for composer tests."""

    def arbitrate(self, request: SCPRequest) -> ArbitrationDecision:
        from semantic.arbitration import SemanticArbitrationLayer

        return SemanticArbitrationLayer().arbitrate(request)


if __name__ == "__main__":
    unittest.main()
