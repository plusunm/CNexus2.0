"""Tests for negotiation conflict gateway service."""

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
        mod.__package__ = name.rsplit(".", 1)[0] if "." in name else pkg
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    state_mod = load(f"{pkg}.state", "state.py")
    negotiation_mod = load(f"{pkg}.services.negotiation", os.path.join("services", "negotiation.py"))
    return state_mod, negotiation_mod


class _FakePrune:
    def __init__(self):
        self.refs = []

    def record_block_reference(self, block_id):
        self.refs.append(block_id)


class NegotiationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.negotiation_mod = _load_modules()

    def _service(self, engine, *, prune=None):
        return self.negotiation_mod.NegotiationService(
            self.state_mod.EngineStateManager(engine),
            self.negotiation_mod.NegotiationHooks(
                get_cognitive_pruning_engine=lambda: prune,
            ),
        )

    def test_conflict_context_empty_buffer(self):
        service = self._service({"negotiation_conflicts": []})
        self.assertEqual(service.conflict_context(), "")

    def test_conflict_context_formats_buffer(self):
        engine = {
            "negotiation_conflicts": [
                {"peer_pubkey": "abcd1234efgh5678", "negotiation_error": "commit_failed"},
            ]
        }
        ctx = self._service(engine).conflict_context()
        self.assertIn("abcd1234efgh", ctx)
        self.assertIn("commit_failed", ctx)

    def test_record_emergent_block_refs(self):
        prune = _FakePrune()
        engine = {
            "negotiation_conflicts": [
                {
                    "pairs": [
                        {"block_id": "b1"},
                        {"block_id": ""},
                        {"block_id": "b2"},
                    ]
                },
                {"pairs": [{"block_id": "b3"}]},
            ]
        }
        self._service(engine, prune=prune).record_emergent_block_refs()
        self.assertEqual(prune.refs, ["b1", "b2", "b3"])

    def test_record_emergent_block_refs_no_prune(self):
        engine = {"negotiation_conflicts": [{"pairs": [{"block_id": "b1"}]}]}
        self._service(engine, prune=None).record_emergent_block_refs()


if __name__ == "__main__":
    unittest.main()
