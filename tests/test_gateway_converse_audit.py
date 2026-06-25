"""Tests for converse audit gateway service."""

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

    for name, fname in (("audit_emitter", "audit_emitter.py"), ("converse_audit", "converse_audit.py")):
        path = os.path.join(GATEWAY_DIR, "services", fname)
        spec = importlib.util.spec_from_file_location(f"{pkg}.services.{name}", path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = f"{pkg}.services"
        sys.modules[f"{pkg}.services.{name}"] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    return sys.modules[f"{pkg}.services.converse_audit"], sys.modules[f"{pkg}.services.audit_emitter"]


class ConverseAuditServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_mod, cls.emitter_mod = _load_modules()

    def _service(self):
        calls = []

        def audit_event(event, data):
            calls.append((event, dict(data)))
            return {"ok": True}

        emitter = self.emitter_mod.AuditEmitter(self.emitter_mod.AuditEmitterHooks(audit_event=audit_event))
        service = self.audit_mod.ConverseAuditService(emitter)
        return service, calls

    def test_skips_when_no_reflection(self):
        service, calls = self._service()
        service.audit_thinking({"use_reflection": False, "thinking_mode": "emergent"}, "t1", "hi")
        self.assertEqual(calls, [])

    def test_emits_emergent_audit_event(self):
        service, calls = self._service()
        profile = {
            "use_reflection": True,
            "thinking_mode": "emergent",
            "global_entropy": "0xabc",
            "temperature": 0.7,
        }
        service.audit_thinking(profile, "trace-42", "hello world")
        self.assertEqual(len(calls), 1)
        event, data = calls[0]
        self.assertEqual(event, "converse.emergent")
        self.assertEqual(data["trace_id"], "trace-42")
        self.assertEqual(data["thinking_mode"], "emergent")
        self.assertEqual(data["global_entropy"], "0xabc")
        self.assertEqual(data["temperature"], 0.7)
        self.assertEqual(data["reply_preview"], "hello world")

    def test_truncates_reply_preview(self):
        service, calls = self._service()
        service.audit_thinking({"use_reflection": True}, "t1", "x" * 600)
        self.assertEqual(len(calls[0][1]["reply_preview"]), 480)


if __name__ == "__main__":
    unittest.main()
