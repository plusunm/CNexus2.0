"""Tests for REM consolidation synthesis."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_synthesis_mod():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    def load(name, relpath):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = name.rsplit(".", 1)[0]
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    load(f"{pkg}.services.converse_thinking", os.path.join("services", "converse_thinking.py"))
    load(f"{pkg}.services.llm", os.path.join("services", "llm.py"))
    return load(f"{pkg}.services.memory.rem_synthesis", os.path.join("services", "memory", "rem_synthesis.py"))


class RemConsolidationSynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_synthesis_mod()

    def test_parse_consolidation_facts_strips_markers(self):
        raw = "1. First useful fact here\n- Second fact line\n* third fact line"
        facts = self.mod.parse_consolidation_facts(raw, max_facts=5)
        self.assertEqual(len(facts), 3)
        self.assertTrue(all(len(f) >= 6 for f in facts))

    def test_heuristic_compact_facts_fallback(self):
        facts = self.mod.heuristic_compact_facts(
            [{"text": "short"}],
            extract_keywords=lambda text, limit: [],
            max_facts=5,
        )
        self.assertEqual(facts, ["近期交互不足以形成新的长期常识节点"])

    def test_synthesize_uses_llm_reply(self):
        synth = self.mod.RemConsolidationSynthesizer(
            self.mod.RemConsolidationSynthesisHooks(
                extract_keywords=lambda text, limit: ["topic"],
                resolve_model_row=lambda _model_id: {
                    "enabled": True,
                    "provider": "ollama",
                    "base_url": "http://127.0.0.1:11434",
                },
                llm_invoke=lambda _row, _prompt: {
                    "reply": "- 用户偏好本地部署模型\n- 关注记忆同步机制",
                },
            ),
        )
        facts = synth.synthesize([{"text": "discuss memory sync"}])
        self.assertGreaterEqual(len(facts), 1)
        self.assertIn("本地部署", facts[0])

    def test_synthesize_heuristic_when_external_disabled(self):
        synth = self.mod.RemConsolidationSynthesizer(
            self.mod.RemConsolidationSynthesisHooks(
                extract_keywords=lambda text, limit: ["memory"],
                resolve_model_row=lambda _model_id: {"enabled": True, "provider": "cnexus"},
                llm_invoke=lambda _row, _prompt: {"reply": "unused"},
            ),
        )
        facts = synth.synthesize([{"text": "we talked about federated memory blocks today"}])
        self.assertTrue(any("memory" in f.lower() or "对话沉淀" in f for f in facts))


if __name__ == "__main__":
    unittest.main()
