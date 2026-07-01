"""Tests for CNexus v1.5 cognitive pipeline (Event + Timeline + State)."""

from __future__ import annotations

import importlib.util
import os
import sys
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


SAMPLE_CONVERSATION = [
    {"timestamp": "2025-04-01 10:00", "speaker": "A", "text": "在干嘛"},
    {"timestamp": "2025-04-01 11:30", "speaker": "B", "text": "在忙"},
    {"timestamp": "2025-04-02 10:00", "speaker": "A", "text": "好久没聊了，最近怎么样"},
    {"timestamp": "2025-04-02 10:02", "speaker": "B", "text": "嗯"},
]


class CognitivePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = _load_module(
            os.path.join("services", "relationship_cognitive_pipeline.py"),
            "cnexus_gateway.services.relationship_cognitive_pipeline",
        )
        cls.canonical = _load_module(
            os.path.join("services", "relationship_canonical.py"),
            "cnexus_gateway.services.relationship_canonical",
        )

    def test_extract_events_message_and_delay(self):
        stream = self.pipeline.extract_events_from_conversation(SAMPLE_CONVERSATION)
        types = [e["type"] for e in stream["events"]]
        self.assertIn("message", types)
        self.assertIn("reply_delay", types)
        self.assertIn("initiative", types)
        self.assertEqual(stream["version"], "1.0")

    def test_build_timeline_segments(self):
        stream = self.pipeline.extract_events_from_conversation(SAMPLE_CONVERSATION)
        timeline = self.pipeline.build_timeline(stream)
        self.assertEqual(timeline["version"], "1.0")
        self.assertTrue(len(timeline["segments"]) >= 1)
        self.assertIn(timeline["currentState"], ("warm", "neutral", "cold", "breaking", "broken"))

    def test_state_transition_on_silence(self):
        conv = [
            {"timestamp": "2025-04-01 10:00", "speaker": "A", "text": "你好呀，今天天气不错"},
            {"timestamp": "2025-04-05 10:00", "speaker": "B", "text": "嗯"},
        ]
        result = self.pipeline.run_cognitive_pipeline(conv, analysis_id="t1")
        self.assertTrue(result["eventStream"]["events"])
        self.canonical.validate_analysis(result["analysis"])
        self.assertIn(result["relationshipState"], ("neutral", "cold", "breaking", "broken"))

    def test_full_pipeline_produces_canonical(self):
        result = self.pipeline.run_cognitive_pipeline(SAMPLE_CONVERSATION, analysis_id="t2")
        self.canonical.validate_analysis(result["analysis"])
        self.assertEqual(result["analysis"]["meta"]["id"], "t2")
        self.assertIn("relationshipStage", result["analysis"]["state"])


if __name__ == "__main__":
    unittest.main()
