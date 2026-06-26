"""Tests for memory protection levels (L0–L3 / Foundation)."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
import time


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
SRC_DIR = os.path.join(ROOT, "src")


def _load_protection():
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)
    pkg = "cnexus_gateway"
    if pkg not in sys.path:
        sys.path.insert(0, GATEWAY_DIR)
    path = os.path.join(GATEWAY_DIR, "services", "memory", "protection.py")
    spec = importlib.util.spec_from_file_location(f"{pkg}.services.memory.protection", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services.memory"
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_memory_control(protection_mod):
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = importlib.util.spec_from_file_location(pkg, init, submodule_search_locations=[GATEWAY_DIR])
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)

    for rel in ("memory/protection.py", "memory_foundation.py", "constitution_loader.py"):
        name = f"{pkg}.services.{rel.replace('/', '.').replace('.py', '')}"
        if name in sys.modules:
            continue
        path = os.path.join(GATEWAY_DIR, "services", rel)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        parts = rel.split("/")
        mod.__package__ = f"{pkg}.services" + (".memory" if len(parts) > 1 else "")
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)

    path = os.path.join(GATEWAY_DIR, "services", "memory_control.py")
    spec = importlib.util.spec_from_file_location(f"{pkg}.services.memory_control", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{pkg}.services"
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_foundation_modules():
    protection = _load_protection()
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)

    def load_service(filename, name):
        path = os.path.join(GATEWAY_DIR, "services", filename)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = "cnexus_gateway.services"
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    foundation = load_service("memory_foundation.py", "cnexus_gateway.services.memory_foundation")
    loader = load_service("constitution_loader.py", "cnexus_gateway.services.constitution_loader")
    return protection, foundation, loader


class _FakeStore:
    def __init__(self, blocks=None):
        self.blocks = list(blocks or [])

    def add(self, block):
        self.blocks.append(block)


class MemoryProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protection = _load_protection()

    def test_infer_foundation_from_manual_filename(self):
        level = self.protection.infer_memory_level_from_ingest("CNexus用户手册.md", "产品哲学与认知演化")
        self.assertEqual(level, "foundation")

    def test_stamp_block_sets_policy_flags(self):
        block = self.protection.stamp_block_protection(
            {
                "block_id": "mem-1",
                "label": "episodic",
                "data": {"filename": "CNexus用户手册.md", "content": "guide"},
                "importance": 0.7,
            },
            "foundation",
        )
        data = block["data"]
        self.assertEqual(data["memory_level"], "foundation")
        self.assertFalse(data["editable"])
        self.assertFalse(data["deletable"])
        self.assertTrue(data["append_only"])
        self.assertTrue(data["locked"])

    def test_retroactive_infer_for_existing_block(self):
        block = {
            "block_id": "mem-old",
            "label": "episodic",
            "data": {"filename": "CNexus实战指南.pdf", "content": "CNexus 认知操作系统"},
        }
        self.assertEqual(self.protection.block_memory_level(block), "foundation")
        self.assertTrue(self.protection.is_clear_protected(block))
        self.assertTrue(self.protection.is_prune_protected(block))

    def test_clear_preserves_constitution_blocks(self):
        protection = self.protection
        control_mod = _load_memory_control(protection)
        preserved = {"count": 0}

        def reset_engine_memory(registry, preserve_constitution=True):
            self.assertTrue(preserve_constitution)
            preserved["count"] = 2

        hooks = control_mod.MemoryControlHooks(
            audit_event=lambda *_a, **_k: None,
            get_current_model_registry=lambda: {"models": []},
            default_model_registry=lambda: {},
            reset_engine_memory=reset_engine_memory,
            persist_file_path=lambda: os.path.join(ROOT, "nonexistent-snapshot.json"),
            append_runtime_log=lambda *_a, **_k: None,
            persist_engine_state=lambda: None,
            persistence_status=lambda: {"ok": True},
        )
        out = control_mod.MemoryControlService(hooks).clear(
            keep_models=True,
            preserve_constitution=True,
        )
        self.assertTrue(out["preserve_constitution"])


class MemoryFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protection, cls.foundation, cls.loader = _load_foundation_modules()

    def test_foundation_upgrade_creates_version_chain(self):
        store = _FakeStore(
            [
                self.protection.stamp_block_protection(
                    {
                        "block_id": "manual-1",
                        "label": "semantic",
                        "data": {
                            "filename": "CNexus用户手册.md",
                            "content": "v1 content",
                            "constitution_key": "CNexus用户手册.md",
                            "memory_version": 1,
                        },
                        "importance": 0.9,
                        "timestamp": time.time(),
                    },
                    "foundation",
                )
            ]
        )

        def mutate(fn):
            return fn(store)

        result = self.foundation.upgrade_foundation_in_store(
            mutate,
            block_id="manual-1",
            content="v2 updated constitution body",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["memory_version"], 2)
        active = [b for b in store.blocks if not (b.get("data") or {}).get("superseded")]
        self.assertEqual(len(active), 1)
        self.assertEqual((active[0].get("data") or {}).get("memory_version"), 2)

    def test_bootstrap_constitution_loads_md(self):
        from runtime.compiler import compile_runtime_sources

        with tempfile.TemporaryDirectory() as tmp:
            constitution_dir = os.path.join(tmp, "runtime", "constitution")
            os.makedirs(constitution_dir)
            path = os.path.join(constitution_dir, "00_test.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# test constitution\nCNexus 认知操作系统")
            compiled = compile_runtime_sources(tmp)
            self.assertEqual(len(compiled.constitution), 1)
            self.assertEqual(compiled.constitution[0].layer, "constitution")

    def test_foundation_version_tree(self):
        blocks = [
            {
                "block_id": "m-v1",
                "data": {
                    "filename": "manual.md",
                    "memory_level": "foundation",
                    "memory_version": 1,
                    "version_label": "v1",
                    "constitution_key": "manual.md",
                    "superseded": True,
                },
            },
            {
                "block_id": "m-v2",
                "data": {
                    "filename": "manual.md",
                    "memory_level": "foundation",
                    "memory_version": 2,
                    "version_label": "v2",
                    "parent_version": "m-v1",
                    "constitution_key": "manual.md",
                },
            },
        ]
        trees = self.foundation.foundation_version_tree(blocks)
        self.assertEqual(len(trees), 1)
        self.assertEqual(trees[0]["active_block_id"], "m-v2")


if __name__ == "__main__":
    unittest.main()
