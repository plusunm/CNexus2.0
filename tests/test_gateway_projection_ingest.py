"""Tests for projection ingest service."""

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

    state_mod = load(f"{pkg}.state", "state.py")
    register_mod = load(f"{pkg}.services.projection_register", os.path.join("services", "projection_register.py"))
    ingest_mod = load(f"{pkg}.services.projection_ingest", os.path.join("services", "projection_ingest.py"))
    return state_mod, register_mod, ingest_mod


class _RegisterStub:
    def register(self, nodes, links, cluster, source_kind="code"):
        return [n["id"] for n in nodes]


class ProjectionIngestServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_mod, cls.register_mod, cls.ingest_mod = _load_modules()

    def _service(self):
        return self.ingest_mod.ProjectionIngestService(
            self.ingest_mod.ProjectionIngestHooks(
                analyze_architecture_image=lambda b64: ([{"id": "n1"}], []),
            ),
            _RegisterStub(),
        )

    def test_ingest_code_ast(self):
        out = self._service().ingest_code({"content": "class A:\n  pass", "file_name": "a.py"})
        self.assertTrue(out["ok"])
        self.assertEqual(out["file"], "a.py")

    def test_project_code_ast_empty(self):
        out = self.ingest_mod.project_code_ast("", "x.py")
        self.assertEqual(out["nodes"], [])


if __name__ == "__main__":
    unittest.main()
