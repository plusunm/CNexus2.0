"""Tests for turn persistence service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
GATEWAY_DIR = os.path.join(SRC, "gateway")
KERNEL_DIR = os.path.join(SRC, "kernel")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load_modules():
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    def load(name, relpath, package):
        path = os.path.join(GATEWAY_DIR, relpath)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = package
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    _load_module = importlib.util.spec_from_file_location
    pipeline_path = os.path.join(KERNEL_DIR, "pipeline.py")
    pipeline_spec = importlib.util.spec_from_file_location("kernel.pipeline", pipeline_path)
    pipeline_mod = importlib.util.module_from_spec(pipeline_spec)
    pipeline_mod.__package__ = "kernel"
    sys.modules["kernel.pipeline"] = pipeline_mod
    assert pipeline_spec.loader is not None
    pipeline_spec.loader.exec_module(pipeline_mod)

    state_mod = load(f"{pkg}.state", "state.py", pkg)
    load(f"{pkg}.services.converse_speech", os.path.join("services", "converse_speech.py"), f"{pkg}.services")
    load(f"{pkg}.services.audit_emitter", os.path.join("services", "audit_emitter.py"), f"{pkg}.services")
    persistence_mod = load(f"{pkg}.services.turn_persistence", os.path.join("services", "turn_persistence.py"), f"{pkg}.services")
    return state_mod, persistence_mod, pipeline_mod


class TurnPersistenceServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.persistence_mod, cls.pipeline_mod = _load_modules()

    def test_commit_turn_writes_trace_and_persists(self):
        engine = {
            "current_iteration": 1,
            "state": object(),
            "memory_store": object(),
            "trace": [],
        }
        calls = {"persist": 0, "audit": 0, "gtbs": 0, "token": 0, "activation": 0}

        audit_emitter_path = os.path.join(GATEWAY_DIR, "services", "audit_emitter.py")
        audit_spec = importlib.util.spec_from_file_location("cnexus_gateway.services.audit_emitter", audit_emitter_path)
        audit_mod = importlib.util.module_from_spec(audit_spec)
        audit_mod.__package__ = "cnexus_gateway.services"
        sys.modules["cnexus_gateway.services.audit_emitter"] = audit_mod
        assert audit_spec.loader is not None
        audit_spec.loader.exec_module(audit_mod)
        audit_emitter = audit_mod.AuditEmitter(
            audit_mod.AuditEmitterHooks(
                audit_event=lambda *a, **k: calls.__setitem__("audit", calls["audit"] + 1),
            )
        )

        service = self.persistence_mod.TurnPersistenceService(
            self.state_mod.EngineStateManager(engine),
            self.persistence_mod.TurnPersistenceHooks(
                store=lambda *a, **k: {"stored": True},
                reflect=lambda *a, **k: {"reflected": True},
                sign_record=lambda row: {"signed": row["trace_id"]},
                record_cycle_gtbs=lambda *a, **k: calls.__setitem__("gtbs", calls["gtbs"] + 1),
                schedule_activation_post_turn=lambda *a, **k: calls.__setitem__("activation", calls["activation"] + 1),
                record_token_trace=lambda *a, **k: calls.__setitem__("token", calls["token"] + 1),
                schedule_persist=lambda: calls.__setitem__("persist", calls["persist"] + 1),
            ),
            audit_emitter,
        )
        package = self.pipeline_mod.TurnCommitPackage(
            input_text="hello",
            obs={"kind": "obs"},
            cog={},
            dec={"intent": "converse"},
            ctx={},
            spk={"text": "hi"},
            model_row={"id": "ollama-local", "provider": "ollama"},
            llm_usage=None,
            token_source="estimated",
            token_mode="fast",
            trace_id="v2-trace-1",
        )
        service.commit_turn(package)
        self.assertEqual(len(engine["trace"]), 1)
        self.assertEqual(engine["trace"][0]["trace_id"], "v2-trace-1")
        self.assertEqual(engine["trace"][0]["identity"]["signed"], "v2-trace-1")
        self.assertEqual(calls["persist"], 1)
        self.assertEqual(calls["audit"], 1)
        self.assertEqual(calls["gtbs"], 1)
        self.assertEqual(calls["token"], 1)
        self.assertEqual(calls["activation"], 1)


if __name__ == "__main__":
    unittest.main()
