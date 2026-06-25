"""Tests for abort-safe external LLM streaming."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
GATEWAY_DIR = os.path.join(SRC, "gateway")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load_llm_module():
    pkg = "cnexus_gateway.services"
    for name, fname in (
        ("converse_thinking", "converse_thinking.py"),
        ("llm", "llm.py"),
    ):
        path = os.path.join(GATEWAY_DIR, "services", fname)
        spec = importlib.util.spec_from_file_location(f"{pkg}.{name}", path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg
        sys.modules[spec.name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    return sys.modules[f"{pkg}.llm"]


class ExternalLlmStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm_mod = _load_llm_module()

    def _hooks(self, **overrides):
        defaults = dict(
            global_entropy_int=lambda: 42,
        )
        defaults.update(overrides)
        return self.llm_mod.LlmMessageHooks(**defaults)

    def _service(self, hooks=None, provenance=None):
        return self.llm_mod.ExternalLlmService(
            llm_max_tokens=512,
            ollama_keep_alive="30m",
            message_hooks=hooks or self._hooks(),
            provenance=provenance,
            default_mode_profile=lambda: {"inject_memory": False},
        )

    def test_build_messages_precision_with_provenance(self):
        class Prov:
            @staticmethod
            def build_preamble():
                return "PROV:"

        service = self._service(provenance=Prov())
        messages = service.build_messages(
            "hello",
            "memory snippet",
            inject_memory=True,
            mode_profile={"thinking_mode": "precision", "provenance_enforced": True},
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("PROV:", messages[0]["content"])
        self.assertIn("memory snippet", messages[0]["content"])
        self.assertEqual(messages[1], {"role": "user", "content": "hello"})

    def test_build_messages_emergent(self):
        service = self._service()
        messages = service.build_messages(
            "ping",
            "ctx",
            inject_memory=True,
            mode_profile={"thinking_mode": "emergent", "global_entropy_int": 7},
        )
        self.assertIn("EMERGENT", messages[0]["content"])
        self.assertIn("ping", messages[0]["content"])
        self.assertIn("ctx", messages[0]["content"])

    def test_stream_closes_http_on_client_abort(self):
        service = self._service()
        model_row = {
            "id": "ollama-local",
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3.2",
            "enabled": True,
        }
        chunks = [
            json.dumps({"message": {"content": "hel"}, "done": False}).encode("utf-8") + b"\n",
            json.dumps({"message": {"content": "lo"}, "done": False}).encode("utf-8") + b"\n",
            json.dumps({"message": {"content": ""}, "done": True, "prompt_eval_count": 1, "eval_count": 2}).encode(
                "utf-8"
            )
            + b"\n",
        ]

        class FakeResp:
            def __init__(self):
                self.closed = False
                self._stream = io.BytesIO(b"".join(chunks))

            def readline(self):
                return self._stream.readline()

            def __iter__(self):
                while True:
                    line = self.readline()
                    if not line:
                        break
                    yield line

            def close(self):
                self.closed = True

        fake_resp = FakeResp()

        with mock.patch("urllib.request.urlopen", return_value=fake_resp):
            gen = service.iter_stream(model_row, "hi")
            self.assertEqual(next(gen), ("token", "hel"))
            gen.close()

        self.assertTrue(fake_resp.closed)

    def test_stream_yields_done_with_usage(self):
        service = self._service()
        model_row = {
            "id": "ollama-local",
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3.2",
            "enabled": True,
        }
        payload = json.dumps(
            {"message": {"content": "ok"}, "done": True, "prompt_eval_count": 3, "eval_count": 2}
        ).encode("utf-8")
        fake_resp = io.BytesIO(payload + b"\n")

        with mock.patch("urllib.request.urlopen", return_value=fake_resp):
            events = list(service.iter_stream(model_row, "ping"))

        self.assertEqual(events[0], ("token", "ok"))
        self.assertEqual(events[1][0], "done")
        self.assertEqual(events[1][1]["reply"], "ok")
        self.assertEqual(events[1][1]["tokens_in"], 3)
        self.assertEqual(events[1][1]["tokens_out"], 2)

    def test_invoke_with_simple_messages(self):
        service = self._service()
        model_row = {
            "id": "ollama-local",
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3.2",
            "enabled": True,
        }
        payload = json.dumps(
            {"message": {"content": "reflect"}, "done": True, "prompt_eval_count": 1, "eval_count": 2}
        ).encode("utf-8")
        fake_resp = io.BytesIO(payload)

        with mock.patch("urllib.request.urlopen", return_value=fake_resp):
            result = service.invoke_with_messages(
                model_row,
                self.llm_mod.ExternalLlmService.build_simple_messages("sys", "user"),
                mode_profile={"inject_memory": False, "temperature": 0.2},
            )

        self.assertEqual(result["reply"], "reflect")


if __name__ == "__main__":
    unittest.main()
