"""Pipeline echo guard tests."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
KERNEL_DIR = os.path.join(SRC, "kernel")
GATEWAY_DIR = os.path.join(SRC, "gateway")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load(name, path, package):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class PipelineEchoGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for mod_name, rel in (
            ("kernel.converse_events", "converse_events.py"),
            ("kernel.speak_reducer", "speak_reducer.py"),
            ("kernel.pipeline", "pipeline.py"),
        ):
            _load(mod_name, os.path.join(KERNEL_DIR, rel), "kernel")

    def test_guard_replaces_verbatim_echo(self):
        from kernel.pipeline import _guard_reply_against_echo

        out = _guard_reply_against_echo("你好", "你好")
        self.assertNotEqual(out.strip(), "你好")
        self.assertTrue(len(out) > 4)


if __name__ == "__main__":
    unittest.main()
