"""SCP P2 — MMR, expert producer, drift signals, SBSL correction feedback."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from plugins.expert_distill.producer import ExpertCandidateProducer
from semantic.arbitration import SemanticArbitrationLayer
from semantic.dimensions import DIMENSION_FACT, DIMENSION_STYLE
from semantic.mmr import mmr_select
from semantic.types import SCPRequest, SemanticBudgetState, SemanticCandidate, TurnProfile


class MMRTests(unittest.TestCase):
    def test_mmr_prefers_diverse_facts(self):
        candidates = [
            SemanticCandidate(block_id="a", dimension="fact", content="python asyncio patterns", score=0.9),
            SemanticCandidate(block_id="b", dimension="fact", content="python asyncio patterns guide", score=0.85),
            SemanticCandidate(block_id="c", dimension="fact", content="database indexing strategies", score=0.7),
        ]
        picked = mmr_select(
            candidates,
            "python database",
            limit=3,
            quotas={DIMENSION_FACT: 1.0},
        )
        ids = {c.block_id for c in picked}
        self.assertGreaterEqual(len(picked), 2)
        self.assertNotEqual(ids, {"a", "b"})
        self.assertIn("c", ids)


class ExpertProducerTests(unittest.TestCase):
    def test_produces_subject_scoped_candidates(self):
        blocks = [
            {
                "block_id": "b1",
                "label": "semantic",
                "data": {
                    "subject_id": "expert:alice",
                    "content": "Alice prefers concise analytical writing.",
                    "semantic_dimension": "fact",
                },
            },
            {
                "block_id": "b2",
                "label": "narrative",
                "data": {
                    "subject_id": "expert:alice",
                    "content": "Use formal tone and short paragraphs.",
                    "semantic_dimension": "style",
                },
            },
            {
                "block_id": "b3",
                "label": "semantic",
                "data": {"subject_id": "expert:bob", "content": "Bob unrelated"},
            },
        ]
        producer = ExpertCandidateProducer()
        recall, prompt, fact_hits = producer.produce(
            blocks,
            query="analytical writing",
            subject_id="expert:alice",
            style_source="prompt",
        )
        self.assertEqual(len(recall), 1)
        self.assertEqual(len(prompt), 1)
        self.assertGreaterEqual(fact_hits, 1)


class SALP2Tests(unittest.TestCase):
    def test_pending_style_override_enforced(self):
        sal = SemanticArbitrationLayer()
        request = SCPRequest(
            query="q",
            turn_profile=TurnProfile(style_source="prompt"),
            budget_state=SemanticBudgetState(pending_style_source_override="off"),
            recall_candidates=[
                SemanticCandidate(block_id="r1", dimension="style", content="tone", source="recall"),
            ],
            prompt_candidates=[
                SemanticCandidate(block_id="p1", dimension="style", content="tone guide", source="prompt"),
            ],
        )
        decision = sal.arbitrate(request)
        self.assertFalse(any(c.dimension == DIMENSION_STYLE for c in decision.recall_plan.items))
        self.assertFalse(any(c.dimension == DIMENSION_STYLE for c in decision.prompt_plan.items))

    def test_cross_path_duplicate_excluded(self):
        sal = SemanticArbitrationLayer()
        request = SCPRequest(
            query="q",
            turn_profile=TurnProfile(style_source="prompt"),
            recall_candidates=[
                SemanticCandidate(
                    block_id="r1",
                    dimension="decision",
                    content="duplicate body",
                    content_hash="abc123",
                    source="recall",
                ),
            ],
            prompt_candidates=[
                SemanticCandidate(
                    block_id="p1",
                    dimension="style",
                    content="duplicate body extended",
                    content_hash="abc123",
                    source="prompt",
                ),
            ],
        )
        decision = sal.arbitrate(request)
        self.assertEqual(len(decision.recall_plan.items), 0)
        self.assertTrue(any(ex.reason == "cross_path_duplicate" for ex in decision.exclusions))


class ConverseConfigExpertTests(unittest.TestCase):
    def test_parse_expert_profile(self):
        import importlib.util

        gateway_dir = os.path.join(SRC, "gateway")
        pkg = "cnexus_gateway_p2"
        init = os.path.join(gateway_dir, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[gateway_dir])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        cfg_path = os.path.join(gateway_dir, "services", "converse_config.py")
        spec2 = importlib.util.spec_from_file_location(f"{pkg}.services.converse_config", cfg_path)
        mod = importlib.util.module_from_spec(spec2)
        mod.__package__ = f"{pkg}.services"
        sys.modules[f"{pkg}.services.converse_config"] = mod
        for dep in ("converse_thinking.py",):
            p = os.path.join(gateway_dir, "services", dep)
            n = f"{pkg}.services.{dep[:-3]}"
            s = importlib.util.spec_from_file_location(n, p)
            m = importlib.util.module_from_spec(s)
            m.__package__ = f"{pkg}.services"
            sys.modules[n] = m
            assert s.loader is not None
            s.loader.exec_module(m)
        assert spec2.loader is not None
        spec2.loader.exec_module(mod)
        svc = mod.ConverseConfigService(
            activation_threshold=0.75,
            inject_limit=2,
            inject_desc_max=80,
            llm_max_tokens=1024,
            converse_modes=frozenset({"fast", "deep", "raw"}),
            hooks=mod.ConverseConfigHooks(global_entropy_int=lambda: 0),
        )
        expert, style = svc.parse_expert_profile(
            {"expert_mode": "expert:alice", "expert_style_source": "recall"}
        )
        self.assertEqual(expert, "expert:alice")
        self.assertEqual(style, "recall")


if __name__ == "__main__":
    unittest.main()
