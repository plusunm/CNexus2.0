"""Tests for gateway intent service."""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "src", "gateway")
SRC_DIR = os.path.join(ROOT, "src")


def _load_modules():
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

    def load(name, filename):
        path = os.path.join(GATEWAY_DIR, "services", filename)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = f"{pkg}.services"
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    intent_mod = load(f"{pkg}.services.gateway_intent", "gateway_intent.py")
    load(f"{pkg}.services.converse", "converse.py")
    load(f"{pkg}.services.ingest", "ingest.py")
    return intent_mod


class _ConverseStub:
    def __init__(self, *, reply_prefix="hello", error=None):
        self._reply_prefix = reply_prefix
        self._error = error

    def run_blocking(self, text, **kwargs):
        if self._error:
            raise self._error
        return {"reply": f"{self._reply_prefix}:{text}"}


class _IngestStub:
    def process_staged(self, file_id, policy):
        return {"file_id": file_id, "processed": True, "policy": policy}

    def process_staged_batch(self, file_ids, policy):
        return {"ok": True, "count": len(file_ids), "indexed": [{"file_id": fid} for fid in file_ids]}

    def process_staged_batch_streaming(self, file_ids, policy, on_progress=None):
        if on_progress:
            on_progress(status="processing", done=0, total=len(file_ids), details=[])
            on_progress(status="processing", done=len(file_ids), total=len(file_ids), details=[])
        return self.process_staged_batch(file_ids, policy)


class GatewayIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svc_mod = _load_modules()

    def _service(self, *, converse_reply="hello", converse_error=None):
        return self.svc_mod.GatewayIntentService(
            _ConverseStub(reply_prefix=converse_reply, error=converse_error),
            _IngestStub(),
        )

    def test_chat_prepare(self):
        out = self._service().handle({"type": "chat_prepare", "payload": {"text": "hi"}})
        self.assertTrue(out["ok"])
        self.assertEqual(out["result"]["user_message"], "hi")

    def test_chat_confirm_uses_prepare_cache(self):
        svc = self._service()
        prep = svc.handle({"type": "chat_prepare", "trace_id": "t1", "payload": {"text": "cached msg"}})
        out = svc.handle({"type": "chat_confirm", "payload": {"prepare_id": prep["trace_id"]}})
        self.assertIn("cached msg", out["result"]["reply"])

    def test_file_process_queues_background(self):
        done = threading.Event()

        class SlowIngest(_IngestStub):
            def process_staged(self, file_id, policy):
                done.wait(timeout=2)
                return {"file_id": file_id, "processed": True, "policy": policy}

        svc = self.svc_mod.GatewayIntentService(_ConverseStub(), SlowIngest())
        out = svc.handle({"type": "file_process", "trace_id": "t-file", "payload": {"file_id": "f-1"}})
        self.assertEqual(out["status"], "queued")
        self.assertEqual(out["trace_id"], "t-file")
        job = svc.get_job("t-file")
        self.assertEqual(job["status"], "queued")
        done.set()
        time.sleep(0.05)
        job = svc.get_job("t-file")
        self.assertTrue(job.get("ok"))
        self.assertEqual(job["status"], "completed")

    def test_default_text_converse(self):
        out = self._service().handle({"payload": {"message": "ping"}})
        self.assertIn("ping", out["result"]["reply"])


if __name__ == "__main__":
    unittest.main()
