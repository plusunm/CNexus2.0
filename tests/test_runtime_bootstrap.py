"""Runtime BOOT — Constitution compiler tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from runtime.bootstrap import boot_runtime
from runtime.compiler import compile_runtime_sources, read_compiled_bundle, write_compiled_bundle
from runtime.context import build_runtime_system_prompt


class RuntimeBootstrapTests(unittest.TestCase):
    def test_compile_and_load_constitution_bin(self):
        with tempfile.TemporaryDirectory() as app_root:
            constitution_dir = os.path.join(app_root, "runtime", "constitution")
            policy_dir = os.path.join(app_root, "runtime", "policy")
            os.makedirs(constitution_dir)
            os.makedirs(policy_dir)
            with open(os.path.join(constitution_dir, "cognitive_constitution.md"), "w", encoding="utf-8") as handle:
                handle.write("# Constitution\nCNexus Cognitive OS")
            with open(os.path.join(policy_dir, "reasoning_policy.md"), "w", encoding="utf-8") as handle:
                handle.write("# Policy\nAlways reason before answer.")

            data_dir = os.path.join(app_root, "data", "runtime")
            result = boot_runtime(app_root, data_dir=data_dir, force_recompile=True)
            self.assertTrue(result["status"]["ok"])
            self.assertEqual(result["status"]["constitution_docs"], 1)
            self.assertEqual(result["status"]["policy_docs"], 1)
            prompt = build_runtime_system_prompt(result["compiled"])
            self.assertIn("CNexus Cognitive OS", prompt)
            self.assertIn("Always reason before answer", prompt)

            bin_path = os.path.join(data_dir, "constitution.bin")
            self.assertTrue(os.path.isfile(bin_path))
            with open(bin_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertIn("constitution", payload)
            self.assertTrue(payload.get("content_signature"))

    def test_bundle_signature_verification(self):
        from runtime.compiler import compute_bundle_signature, verify_compiled_bundle

        with tempfile.TemporaryDirectory() as app_root:
            constitution_dir = os.path.join(app_root, "runtime", "constitution")
            os.makedirs(constitution_dir)
            with open(os.path.join(constitution_dir, "test.md"), "w", encoding="utf-8") as handle:
                handle.write("# Test\nsignature check")
            data_dir = os.path.join(app_root, "data", "runtime")
            result = boot_runtime(app_root, data_dir=data_dir, force_recompile=True)
            compiled = result["compiled"]
            self.assertTrue(verify_compiled_bundle(compiled))
            self.assertEqual(compiled.content_signature, compute_bundle_signature(compiled))
            path = write_compiled_bundle(compiled, data_dir)
            loaded = read_compiled_bundle(data_dir, verify=True)
            self.assertIsNotNone(loaded)
            with open(path, "r", encoding="utf-8") as handle:
                tampered = json.load(handle)
            tampered["constitution"][0]["content"] = "hacked"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(tampered, handle)
            self.assertIsNone(read_compiled_bundle(data_dir, verify=True))

    def test_ed25519_sign_and_verify(self):
        from core.identity_manager import IdentityManager
        from runtime.compiler import compile_runtime_sources, write_compiled_bundle
        from runtime.signing import verify_ed25519_bundle
        from runtime.compiler import read_compiled_bundle_raw

        with tempfile.TemporaryDirectory() as app_root:
            constitution_dir = os.path.join(app_root, "runtime", "constitution")
            os.makedirs(constitution_dir)
            with open(os.path.join(constitution_dir, "test.md"), "w", encoding="utf-8") as handle:
                handle.write("# Test\ned25519")
            data_dir = os.path.join(app_root, "data", "runtime")
            im = IdentityManager(os.path.join(app_root, "identity.key"))
            compiled = compile_runtime_sources(app_root)
            write_compiled_bundle(compiled, data_dir, identity_manager=im)
            raw = read_compiled_bundle_raw(data_dir) or {}
            self.assertTrue(verify_ed25519_bundle(raw, im))
            self.assertTrue(raw.get("bundle_signature"))
        compiled = compile_runtime_sources(ROOT)
        prompt = build_runtime_system_prompt(compiled)
        self.assertIn("CNexus Runtime", prompt)
        self.assertGreater(len(compiled.constitution), 0)
        self.assertGreater(len(compiled.policy), 0)


class FoundationVersionTreeTests(unittest.TestCase):
    def test_version_tree_branching(self):
        from gateway.services.memory_foundation import foundation_version_tree

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
                "block_id": "m-v1.1",
                "data": {
                    "filename": "manual.md",
                    "memory_level": "foundation",
                    "memory_version": 2,
                    "version_label": "v1.1",
                    "parent_version": "m-v1",
                    "constitution_key": "manual.md",
                    "superseded": True,
                },
            },
            {
                "block_id": "m-v2",
                "data": {
                    "filename": "manual.md",
                    "memory_level": "foundation",
                    "memory_version": 3,
                    "version_label": "v2",
                    "parent_version": "m-v1.1",
                    "constitution_key": "manual.md",
                },
            },
        ]
        trees = foundation_version_tree(blocks)
        self.assertEqual(len(trees), 1)
        self.assertEqual(trees[0]["active_block_id"], "m-v2")
        self.assertEqual(len(trees[0]["versions"]), 3)


if __name__ == "__main__":
    unittest.main()
