"""Tests for Memory Domain context + provenance services."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_modules():
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

    load(f"{pkg}.services.memory.types", os.path.join("services", "memory", "types.py"))
    prov_mod = load(f"{pkg}.services.memory.provenance", os.path.join("services", "memory", "provenance.py"))
    context_mod = load(f"{pkg}.services.memory.context", os.path.join("services", "memory", "context.py"))
    return prov_mod, context_mod


class MemoryContextServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prov_mod, cls.context_mod = _load_modules()

    def test_format_activation_context(self):
        prov = self.prov_mod.DefaultProvenancePort()
        service = self.context_mod.MemoryContextService(prov, default_desc_max=10)
        hits = [
            (
                0.8,
                {
                    "id": "a",
                    "tag": "term",
                    "title": "Alpha",
                    "desc": "long description text",
                },
            )
        ]
        text = service.format_activation_context(hits, desc_max=10)
        self.assertIn("[term] Alpha", text)
        self.assertIn("activation=0.80", text)
        self.assertIn("long descr", text)

    def test_build_recall_context_with_trace_preview(self):
        prov = self.prov_mod.DefaultProvenancePort()
        service = self.context_mod.MemoryContextService(prov)
        from cnexus_gateway.services.memory.types import MemoryFragment, RecallResult, TraceEntry

        result = RecallResult(
            query="neural",
            fragments=[],
            trace_entries=[
                TraceEntry(text="neural memory recall", replayed=True, trace_id="t1"),
            ],
        )
        text = service.build_recall_context(result)
        self.assertIn("neural memory recall", text)
        self.assertIn("Audit-Preview", text)

    def test_build_preamble(self):
        prov = self.prov_mod.DefaultProvenancePort()
        service = self.context_mod.MemoryContextService(prov)
        self.assertIn("Provenance honesty", service.build_precision_preamble())


if __name__ == "__main__":
    unittest.main()
