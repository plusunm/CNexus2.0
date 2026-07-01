"""External LLM streaming/blocking — abort-safe, no app_v2 imports."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib import request as urlrequest

logger = logging.getLogger("cnexus.llm")

from .converse_thinking import build_emergent_system_content, build_precision_system_content
from .provider_health import ProviderHealthGate

DefaultModeProfileFn = Callable[[], Dict[str, Any]]
GlobalEntropyIntFn = Callable[[], int]

_BASE_CHAT_SYSTEM = (
    "你是 CNexus 2.0 个人认知助手。用自然、简洁的中文回答用户。"
    "不要重复、照抄或只做同义改写用户的原话；应给出新的有用信息。"
)


@dataclass(frozen=True)
class LlmMessageHooks:
    """Inject entropy — provenance lives on ProvenancePort."""

    global_entropy_int: GlobalEntropyIntFn


def build_chat_messages(
    user_text: str,
    memory_context: Optional[str],
    *,
    inject_memory: bool,
    mode_profile: Optional[Dict[str, Any]],
    hooks: LlmMessageHooks,
    provenance: Any = None,
) -> List[Dict[str, str]]:
    profile = mode_profile or {}
    thinking_mode = profile.get("thinking_mode", "precision")
    messages: List[Dict[str, str]] = []
    if inject_memory:
        ctx = (memory_context or "").strip()
        if ctx or thinking_mode == "emergent":
            if thinking_mode == "emergent":
                entropy = int(profile.get("global_entropy_int") or hooks.global_entropy_int())
                content = build_emergent_system_content(user_text, ctx, entropy)
            else:
                preamble = ""
                if provenance and profile.get("provenance_enforced", True):
                    preamble = provenance.build_preamble()
                content = build_precision_system_content(ctx, provenance_preamble=preamble)
            messages.append({"role": "system", "content": content})
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": _BASE_CHAT_SYSTEM})
    messages.append({"role": "user", "content": user_text})
    return messages


class ExternalLlmService:
    """Ollama / OpenAI-compatible chat — closes HTTP on generator abort."""

    def __init__(
        self,
        *,
        llm_max_tokens: int,
        ollama_keep_alive: str,
        message_hooks: LlmMessageHooks,
        provenance: Any = None,
        default_mode_profile: DefaultModeProfileFn,
        health_gate: Optional[ProviderHealthGate] = None,
    ):
        self._llm_max_tokens = llm_max_tokens
        self._ollama_keep_alive = ollama_keep_alive
        self._message_hooks = message_hooks
        self._provenance = provenance
        self._default_mode_profile = default_mode_profile
        self._health = health_gate or ProviderHealthGate()

    def open_timeout(self, model_row: Dict[str, Any], *, streaming: bool) -> float:
        provider = str(model_row.get("provider") or "")
        if provider == "ollama":
            raw = os.environ.get("CNEXUS_OLLAMA_OPEN_TIMEOUT", "30").strip()
        else:
            raw = os.environ.get("CNEXUS_LLM_OPEN_TIMEOUT", "12").strip()
        try:
            return max(3.0, float(raw))
        except ValueError:
            return 30.0 if provider == "ollama" else 12.0

    def should_use_external_for_chat(self, model_row: Any) -> bool:
        if not ExternalLlmService.should_use_external(model_row):
            return False
        return self._health.allow(model_row)

    def build_messages(
        self,
        user_text: str,
        memory_context: Optional[str] = None,
        *,
        inject_memory: bool = True,
        mode_profile: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        return build_chat_messages(
            user_text,
            memory_context,
            inject_memory=inject_memory,
            mode_profile=mode_profile,
            hooks=self._message_hooks,
            provenance=self._provenance,
        )

    @staticmethod
    def should_use_external(model_row: Any) -> bool:
        if not model_row or not model_row.get("enabled", True):
            return False
        provider = model_row.get("provider", "")
        if provider in ("cnexus", ""):
            return False
        if provider == "ollama":
            return True
        return bool((model_row.get("api_key") or "").strip())

    @staticmethod
    def chat_url(model_row: Dict[str, Any]) -> str:
        base = (model_row.get("base_url") or "").rstrip("/")
        provider = model_row.get("provider", "")
        if provider == "ollama" or ":11434" in base:
            return f"{base}/api/chat"
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def ollama_chat_options(self, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        profile = profile or {}
        opts = {"num_predict": int(profile.get("llm_max_tokens") or self._llm_max_tokens)}
        temp = profile.get("temperature")
        if temp is not None:
            try:
                opts["temperature"] = max(0.0, min(float(temp), 1.5))
            except (TypeError, ValueError):
                pass
        num_ctx = profile.get("num_ctx")
        if num_ctx:
            try:
                opts["num_ctx"] = int(num_ctx)
            except (TypeError, ValueError):
                pass
        else:
            for key, env_name in (("num_ctx", "CNEXUS_OLLAMA_NUM_CTX"), ("num_thread", "CNEXUS_OLLAMA_NUM_THREAD")):
                raw = os.environ.get(env_name, "").strip()
                if not raw:
                    continue
                try:
                    opts[key] = int(raw)
                except ValueError:
                    pass
        return opts

    @staticmethod
    def request_headers(model_row: Dict[str, Any], is_ollama: bool) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = (model_row.get("api_key") or "").strip()
        if api_key and not is_ollama:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    @staticmethod
    def estimate_tokens(text: Any) -> int:
        if not text:
            return 0
        return max(1, int(len(str(text)) * 0.75))

    @staticmethod
    def build_simple_messages(system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": str(system_prompt or "")},
            {"role": "user", "content": str(user_prompt or "")},
        ]

    def _compose_request(
        self,
        model_row: Dict[str, Any],
        messages: List[Dict[str, str]],
        profile: Dict[str, Any],
        *,
        stream: bool,
    ) -> Tuple[str, Dict[str, Any], bool]:
        url = self.chat_url(model_row)
        provider = model_row.get("provider", "")
        is_ollama = provider == "ollama" or "/api/chat" in url
        body: Dict[str, Any] = {
            "model": model_row.get("model") or "llama3.2",
            "messages": messages,
            "stream": stream,
        }
        if is_ollama:
            body["options"] = self.ollama_chat_options(profile)
            if self._ollama_keep_alive:
                body["keep_alive"] = self._ollama_keep_alive
        elif profile.get("temperature") is not None:
            body["temperature"] = max(0.0, min(float(profile.get("temperature")), 1.5))
        return url, body, is_ollama

    def _request_body(
        self,
        model_row: Dict[str, Any],
        user_text: str,
        memory_context: Optional[str],
        profile: Dict[str, Any],
        *,
        stream: bool,
    ) -> Tuple[str, Dict[str, Any], bool]:
        messages = self.build_messages(
            user_text,
            memory_context,
            inject_memory=bool(profile.get("inject_memory", True)),
            mode_profile=profile,
        )
        return self._compose_request(model_row, messages, profile, stream=stream)

    @staticmethod
    def _parse_chat_response(payload: Dict[str, Any], is_ollama: bool) -> Tuple[str, int, int]:
        if is_ollama:
            reply = str((payload.get("message") or {}).get("content") or "")
            tokens_in = int(payload.get("prompt_eval_count") or 0)
            tokens_out = int(payload.get("eval_count") or 0)
        else:
            reply = str((payload.get("choices") or [{}])[0].get("message", {}).get("content") or "")
            usage = payload.get("usage") or {}
            tokens_in = int(usage.get("prompt_tokens") or 0)
            tokens_out = int(usage.get("completion_tokens") or 0)
        return reply, tokens_in, tokens_out

    def invoke_with_messages(
        self,
        model_row: Dict[str, Any],
        messages: List[Dict[str, str]],
        mode_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Blocking chat with caller-supplied messages (reflection, emergent agents, etc.)."""
        profile = dict(mode_profile or {})
        profile.setdefault("inject_memory", False)
        url, body, is_ollama = self._compose_request(model_row, messages, profile, stream=False)
        data = json.dumps(body).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=data,
            headers=self.request_headers(model_row, is_ollama),
            method="POST",
        )
        timeout = self.open_timeout(model_row, streaming=False)
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            self._health.record_failure(model_row)
            raise
        self._health.record_success(model_row)

        reply, tokens_in, tokens_out = self._parse_chat_response(payload, is_ollama)
        provider = model_row.get("provider", "")
        user_text = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if not reply.strip():
            raise ValueError("LLM 返回空回复")
        if tokens_in <= 0:
            tokens_in = self.estimate_tokens(user_text)
        if tokens_out <= 0:
            tokens_out = self.estimate_tokens(reply)
        return {
            "reply": reply.strip(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "provider": provider,
            "model_id": model_row.get("id"),
        }

    def invoke_messages(
        self,
        model_row: Dict[str, Any],
        messages: List[Dict[str, str]],
        mode_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        profile = mode_profile or self._default_mode_profile()
        url, body, is_ollama = self._compose_request(model_row, messages, profile, stream=False)
        data = json.dumps(body).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=data,
            headers=self.request_headers(model_row, is_ollama),
            method="POST",
        )
        timeout = self.open_timeout(model_row, streaming=False)
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            self._health.record_failure(model_row)
            raise
        self._health.record_success(model_row)

        reply, tokens_in, tokens_out = self._parse_chat_response(payload, is_ollama)
        provider = model_row.get("provider", "")
        if not reply.strip():
            raise ValueError("LLM 返回空回复")
        user_text = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if tokens_in <= 0:
            tokens_in = self.estimate_tokens(user_text)
        if tokens_out <= 0:
            tokens_out = self.estimate_tokens(reply)
        return {
            "reply": reply.strip(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "provider": provider,
            "model_id": model_row.get("id"),
        }

    def invoke(
        self,
        model_row: Dict[str, Any],
        user_text: str,
        memory_context: Optional[str] = None,
        mode_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        profile = mode_profile or self._default_mode_profile()
        url, body, is_ollama = self._request_body(
            model_row,
            user_text,
            memory_context,
            profile,
            stream=False,
        )
        data = json.dumps(body).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=data,
            headers=self.request_headers(model_row, is_ollama),
            method="POST",
        )
        timeout = self.open_timeout(model_row, streaming=False)
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            self._health.record_failure(model_row)
            raise
        self._health.record_success(model_row)

        reply, tokens_in, tokens_out = self._parse_chat_response(payload, is_ollama)
        provider = model_row.get("provider", "")
        if not reply.strip():
            raise ValueError("LLM 返回空回复")
        if tokens_in <= 0:
            tokens_in = self.estimate_tokens(user_text)
        if tokens_out <= 0:
            tokens_out = self.estimate_tokens(reply)
        return {
            "reply": reply.strip(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "provider": provider,
            "model_id": model_row.get("id"),
        }

    def iter_stream(
        self,
        model_row: Dict[str, Any],
        user_text: str,
        memory_context: Optional[str] = None,
        mode_profile: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Tuple[str, Any]]:
        """Yield ('token', chunk) then ('done', usage). Closes HTTP on GeneratorExit."""
        profile = mode_profile or self._default_mode_profile()
        url, body, is_ollama = self._request_body(
            model_row,
            user_text,
            memory_context,
            profile,
            stream=True,
        )
        data = json.dumps(body).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=data,
            headers=self.request_headers(model_row, is_ollama),
            method="POST",
        )
        provider = model_row.get("provider", "")
        reply_parts: list[str] = []
        tokens_in = 0
        tokens_out = 0
        resp = None
        aborted = False
        try:
            resp = urlrequest.urlopen(req, timeout=self.open_timeout(model_row, streaming=True))
            if is_ollama:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    chunk = str((obj.get("message") or {}).get("content") or "")
                    if chunk:
                        reply_parts.append(chunk)
                        yield ("token", chunk)
                    if obj.get("done"):
                        tokens_in = int(obj.get("prompt_eval_count") or 0)
                        tokens_out = int(obj.get("eval_count") or 0)
                        break
            else:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    chunk = str(((obj.get("choices") or [{}])[0].get("delta") or {}).get("content") or "")
                    if chunk:
                        reply_parts.append(chunk)
                        yield ("token", chunk)
                    usage = obj.get("usage") or {}
                    if usage:
                        tokens_in = int(usage.get("prompt_tokens") or tokens_in)
                        tokens_out = int(usage.get("completion_tokens") or tokens_out)
        except GeneratorExit:
            aborted = True
            logger.warning("LLM stream aborted — closing HTTP connection to %s", url)
            raise
        except Exception:
            self._health.record_failure(model_row)
            raise
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass
            if aborted:
                logger.info("LLM GPU/compute leak prevented for provider=%s model=%s", provider, model_row.get("model"))

        reply = "".join(reply_parts).strip()
        if not reply:
            self._health.record_failure(model_row)
            raise ValueError("LLM 返回空回复")
        self._health.record_success(model_row)
        if tokens_in <= 0:
            tokens_in = self.estimate_tokens(user_text)
        if tokens_out <= 0:
            tokens_out = self.estimate_tokens(reply)
        yield (
            "done",
            {
                "reply": reply,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "provider": provider,
                "model_id": model_row.get("id"),
            },
        )
