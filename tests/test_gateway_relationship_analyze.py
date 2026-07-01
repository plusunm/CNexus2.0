"""Tests for relationship canonical schema + analyze service."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
SRC_DIR = os.path.join(ROOT, "src")


def _load_module(relpath: str, name: str):
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)
    path = os.path.join(GATEWAY_DIR, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = name.rsplit(".", 1)[0]
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class RelationshipCanonicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = _load_module(
            os.path.join("services", "relationship_canonical.py"),
            "cnexus_gateway.services.relationship_canonical",
        )
        cls.cards = _load_module(
            os.path.join("services", "relationship_cards.py"),
            "cnexus_gateway.services.relationship_cards",
        )
        _load_module(
            os.path.join("services", "relationship_llm_prompt.py"),
            "cnexus_gateway.services.relationship_llm_prompt",
        )
        _load_module(
            os.path.join("services", "relationship_model_ontology.py"),
            "cnexus_gateway.services.relationship_model_ontology",
        )
        _load_module(
            os.path.join("services", "relationship_decision_library.py"),
            "cnexus_gateway.services.relationship_decision_library",
        )
        _load_module(
            os.path.join("services", "relationship_card_model.py"),
            "cnexus_gateway.services.relationship_card_model",
        )
        _load_module(
            os.path.join("services", "relationship_card_llm_prompt.py"),
            "cnexus_gateway.services.relationship_card_llm_prompt",
        )
        cls.analyze = _load_module(
            os.path.join("services", "relationship_analyze.py"),
            "cnexus_gateway.services.relationship_analyze",
        )

    def test_rule_based_analysis_validates(self):
        converse = {
            "emotion": {"valence": -0.3, "arousal": 0.4},
            "activation_injected": 0,
            "activation_hits": [],
            "intent": "converse",
        }
        analysis = self.canonical.rule_based_analysis("他最近不理我", converse, {})
        self.canonical.validate_analysis(analysis)
        self.assertEqual(analysis["state"]["relationshipStage"], "cold")
        self.assertIn("A", analysis["decision"]["options"])

    def test_normalize_llm_snake_case_payload(self):
        llm_raw = {
            "state": {
                "emotion_connection": "low",
                "initiative_level": "medium",
                "interaction_frequency": "low",
                "relationship_stage": "breaking",
            },
            "signals": {"positive": ["仍存在回应"], "negative": ["回复变慢"]},
            "uncertainty": {
                "missing_info": ["缺少对方近期态度说明"],
                "risk_of_misjudgment": "信息不足可能导致误判",
            },
            "decision": {
                "A": "等待观察",
                "B": "主动沟通验证",
                "C": "降低投入",
                "D": "明确决策",
                "recommended": "B",
                "reason": "互动信号不足，需先验证",
            },
            "actions": ["发起关系状态确认对话"],
        }
        base = self.canonical.rule_based_analysis("他最近不理我", {}, {})
        merged = self.canonical.merge_llm_fill(base, llm_raw)
        self.canonical.validate_analysis(merged)
        self.assertEqual(merged["state"]["relationshipStage"], "broken")
        self.assertEqual(merged["decision"]["recommended"], "B")
        self.assertEqual(merged["uncertainty"]["missingInfo"][0], "缺少对方近期态度说明")

    def test_card_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cards.json")

            def cards_file():
                return path

            store = self.cards.RelationshipCardStore(cards_file=cards_file)
            converse = {"emotion": {"valence": 0.1}, "activation_injected": 2, "activation_hits": []}
            analysis = self.canonical.rule_based_analysis("要不要分手", converse, {}, analysis_id="c1")
            card = self.canonical.to_card_envelope(analysis)
            self.assertIn("problemType", card["card"])
            self.assertIn("modelSummary", card["card"])
            self.assertIn("signalModel", card["card"])
            store.save_card(card)
            loaded = store.list_cards()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["meta"]["id"], "c1")
            self.assertEqual(loaded[0]["card"]["title"], "分手期决策模型")

    def test_rule_based_model_card(self):
        card_model = _load_module(
            os.path.join("services", "relationship_card_model.py"),
            "cnexus_gateway.services.relationship_card_model",
        )
        converse = {"emotion": {"valence": -0.3}, "activation_injected": 0, "activation_hits": []}
        analysis = self.canonical.rule_based_analysis("他最近不理我", converse, {})
        model = card_model.rule_based_model_card(analysis)
        card_model.validate_model_card(model)
        self.assertEqual(model["title"], "冷淡期判断模型")
        self.assertEqual(model["libraryModelId"], "cold_phase")
        self.assertTrue(model["signalModel"]["keyNegativeSignals"])

    def test_model_router_ambiguous(self):
        lib = _load_module(
            os.path.join("services", "relationship_model_ontology.py"),
            "cnexus_gateway.services.relationship_model_ontology",
        )
        converse = {"emotion": {"valence": 0.2}, "activation_injected": 2, "activation_hits": []}
        analysis = self.canonical.rule_based_analysis("暧昧关系要不要推进", converse, {})
        route = lib.route_model(analysis)
        self.assertEqual(route["familyId"], "ambiguous_phase")
        self.assertIn("keyword_ambiguous", route["matchedRules"])

    def test_model_router_breakdown(self):
        lib = _load_module(
            os.path.join("services", "relationship_model_ontology.py"),
            "cnexus_gateway.services.relationship_model_ontology",
        )
        analysis = self.canonical.rule_based_analysis("要不要分手", {}, {})
        route = lib.route_model(analysis)
        self.assertEqual(route["familyId"], "breakdown_phase")

    def test_ontology_card_structure_locked(self):
        onto = _load_module(
            os.path.join("services", "relationship_model_ontology.py"),
            "cnexus_gateway.services.relationship_model_ontology",
        )
        converse = {"emotion": {"valence": -0.3}, "activation_injected": 0, "activation_hits": []}
        analysis = self.canonical.rule_based_analysis("他最近不理我", converse, {})
        route = onto.route_model(analysis)
        card = onto.instantiate_model_card(analysis, route)
        self.assertEqual(len(card["decisionModel"]["triggerConditions"]), 3)
        self.assertEqual(card["title"], "冷淡期判断模型")
        tags = set(card["reusabilityTags"])
        self.assertIn("cold_phase", tags)
        self.assertIn("decision_required", tags)

    def test_analyze_service_returns_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cards.json")

            def cards_file():
                return path

            store = self.cards.RelationshipCardStore(cards_file=cards_file)

            def converse_blocking(text, **kwargs):
                return {
                    "reply": "test",
                    "emotion": {"valence": 0.0, "arousal": 0.5},
                    "activation_injected": 1,
                    "activation_hits": [{"title": "past chat", "score": 0.6}],
                    "intent": "converse",
                }

            service = self.analyze.RelationshipAnalyzeService(
                card_store=store,
                converse_blocking=converse_blocking,
                status_snapshot=lambda: {"relationship": {"trust": 0.5}},
                resolve_model=lambda: None,
                llm_service=None,
                llm_enabled=False,
            )
            result = service.analyze({"text": "他最近不理我", "use_llm": False})
            self.assertTrue(result["ok"])
            self.canonical.validate_analysis(result["analysis"])
            self.assertEqual(result["fill_source"], "rule")
            cards = store.list_cards()
            self.assertEqual(len(cards), 1)

    def test_analyze_fast_skips_converse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cards.json")
            store = self.cards.RelationshipCardStore(cards_file=lambda: path)
            converse_calls = []

            def converse_blocking(text, **kwargs):
                converse_calls.append(text)
                return {"emotion": {"valence": 0.9}}

            service = self.analyze.RelationshipAnalyzeService(
                card_store=store,
                converse_blocking=converse_blocking,
                status_snapshot=lambda: {},
                resolve_model=lambda: None,
                llm_service=None,
                llm_enabled=False,
            )
            result = service.analyze({"text": "他最近不理我", "fast": True})
            self.assertTrue(result["ok"])
            self.assertTrue(result.get("fast"))
            self.assertEqual(converse_calls, [])
            self.canonical.validate_analysis(result["analysis"])

    def test_analyze_converse_failure_degrades(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cards.json")
            store = self.cards.RelationshipCardStore(cards_file=lambda: path)

            def converse_blocking(text, **kwargs):
                raise RuntimeError("converse boom")

            service = self.analyze.RelationshipAnalyzeService(
                card_store=store,
                converse_blocking=converse_blocking,
                status_snapshot=lambda: {},
                resolve_model=lambda: None,
                llm_service=None,
                llm_enabled=False,
            )
            result = service.analyze({"text": "他最近不理我", "use_llm": False})
            self.assertTrue(result["ok"])
            self.assertTrue(result.get("degraded"))
            self.assertTrue(result.get("fast"))
            self.canonical.validate_analysis(result["analysis"])


if __name__ == "__main__":
    unittest.main()
