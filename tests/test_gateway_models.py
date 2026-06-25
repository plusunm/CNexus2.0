"""Unit tests for extracted gateway model service."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")


def _load_module(name: str, relpath: str, package: str):
    path = os.path.join(GATEWAY_DIR, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ModelConfigServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pkg = "cnexus_gateway"
        if pkg not in sys.modules:
            init = os.path.join(GATEWAY_DIR, "__init__.py")
            spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
            module = importlib.util.module_from_spec(spec)
            sys.modules[pkg] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
        cls.state_mod = _load_module(f"{pkg}.state", "state.py", pkg)
        cls.models_mod = _load_module(f"{pkg}.services.models", os.path.join("services", "models.py"), f"{pkg}.services")

    def setUp(self):
        self.persist_calls = 0
        self.engine = {"model_registry": self.models_mod.ModelConfigService.default_registry()}
        self.state = self.state_mod.EngineStateManager(self.engine)
        self.service = self.models_mod.ModelConfigService(
            self.state,
            schedule_persist=self._mark_persist,
            ollama_host="127.0.0.1:11434",
        )

    def _mark_persist(self):
        self.persist_calls += 1

    def test_upsert_cloud_model_sets_api_key(self):
        row, err = self.service.upsert(
            "deepseek-chat",
            {
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-flash",
                "is_default": True,
            },
        )
        self.assertIsNone(err)
        assert row is not None
        self.assertTrue(row["api_key_set"])
        self.assertTrue(row["is_default"])
        self.assertEqual(self.persist_calls, 1)

    def test_test_cloud_model_skips_remote_probe(self):
        self.service.upsert("deepseek-chat", {"api_key": "sk-test"})
        result = self.service.test("deepseek-chat", quick=True)
        self.assertTrue(result["success"])

    def test_active_model_id_prefers_default(self):
        self.service.upsert("deepseek-chat", {"api_key": "sk-test", "is_default": True, "enabled": True})
        self.assertEqual(self.service.active_model_id(), "deepseek-chat")

    def test_resolve_model_row_seeds_builtin_default(self):
        row = self.service.resolve_model_row("deepseek-chat")
        assert row is not None
        self.assertEqual(row["id"], "deepseek-chat")
        self.assertEqual(row["provider"], "openai_compatible")
        seeded = self.engine["model_registry"].get("deepseek-chat")
        self.assertIsNotNone(seeded)

    def test_resolve_model_row_uses_active_when_id_omitted(self):
        self.service.upsert("deepseek-chat", {"api_key": "sk-test", "is_default": True, "enabled": True})
        row = self.service.resolve_model_row(None)
        assert row is not None
        self.assertEqual(row["id"], "deepseek-chat")

    def test_resolve_model_row_for_chat_syncs_ollama(self):
        self.service.upsert(
            "ollama-local",
            {"enabled": True, "provider": "ollama", "model": "llama3.2", "is_default": True},
        )
        calls = {"sync": 0}
        original = self.service.sync_ollama_registry

        def tracked_sync(force=False):
            calls["sync"] += 1
            return original(force=force)

        self.service.sync_ollama_registry = tracked_sync  # type: ignore[method-assign]
        row = self.service.resolve_model_row_for_chat("ollama-local")
        assert row is not None
        self.assertEqual(row["provider"], "ollama")
        self.assertEqual(calls["sync"], 1)

    def test_resolve_model_row_for_chat_skips_sync_for_cloud(self):
        calls = {"sync": 0}
        original = self.service.sync_ollama_registry

        def tracked_sync(force=False):
            calls["sync"] += 1
            return original(force=force)

        self.service.sync_ollama_registry = tracked_sync  # type: ignore[method-assign]
        self.service.upsert("deepseek-chat", {"api_key": "sk-test", "is_default": True, "enabled": True})
        row = self.service.resolve_model_row_for_chat("deepseek-chat")
        assert row is not None
        self.assertEqual(calls["sync"], 0)

    def test_resolve_model_row_for_chat_skips_sync_when_ollama_disabled(self):
        calls = {"sync": 0}
        original = self.service.sync_ollama_registry

        def tracked_sync(force=False):
            calls["sync"] += 1
            return original(force=force)

        self.service.sync_ollama_registry = tracked_sync  # type: ignore[method-assign]
        self.service.upsert("ollama-local", {"enabled": False, "provider": "ollama"})
        row = self.service.resolve_model_row_for_chat("ollama-local")
        assert row is not None
        self.assertEqual(calls["sync"], 0)

    def test_create_custom_model(self):
        row, err = self.service.create(
            {
                "name": "My Model",
                "provider": "openai_compatible",
                "base_url": "https://example.com",
                "model": "demo",
                "api_key": "abc",
            },
        )
        self.assertIsNone(err)
        assert row is not None
        self.assertTrue(row["id"].startswith("custom-"))


if __name__ == "__main__":
    unittest.main()
