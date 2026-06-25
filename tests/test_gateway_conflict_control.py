"""Tests for conflict control service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_module():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    path = os.path.join(GATEWAY_DIR, "services", "conflict_control.py")
    name = f"{pkg}.services.conflict_control"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services"
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _AgentStub:
    @staticmethod
    def entry_from_block(raw, source="local"):
        return {"content": raw.get("content", ""), "source": source}

    @staticmethod
    def entry_from_audit_data(raw, source="remote"):
        return {"content": raw.get("content_preview", ""), "source": source}


class ConflictControlServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def _service(self, *, agent=_AgentStub(), report=None):
        report = report or {"ok": True}
        return self.mod.ConflictControlService(
            self.mod.ConflictControlHooks(
                get_conflict_agent=lambda: agent,
                run_conflict_resolution=lambda *a, **k: report,
                conflict_resolution_status=lambda: {"negotiation_conflict_llm": True},
                set_negotiation_conflict_llm=lambda v: None,
                set_negotiation_conflict_enabled=lambda v: None,
            )
        )

    def test_resolve_missing_content(self):
        payload, status = self._service().resolve({"local": {}, "remote": {}})
        self.assertEqual(status, 400)

    def test_update_settings(self):
        payload, status = self._service().update_settings({"llm_auto_resolve": True})
        self.assertTrue(payload["ok"])
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
