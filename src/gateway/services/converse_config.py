"""Converse mode profiles and thinking-mode inference parameters."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, Optional, Tuple

from .converse_thinking import normalize_thinking_mode, thinking_inference_params

GlobalEntropyIntFn = Callable[[], int]


@dataclass(frozen=True)
class ConverseConfigHooks:
    global_entropy_int: GlobalEntropyIntFn


class ConverseConfigService:
    """Fast/deep/raw converse profiles — no app_v2 imports."""

    def __init__(
        self,
        *,
        activation_threshold: float,
        inject_limit: int,
        inject_desc_max: int,
        llm_max_tokens: int,
        converse_modes: FrozenSet[str],
        hooks: ConverseConfigHooks,
    ):
        self._activation_threshold = activation_threshold
        self._inject_limit = inject_limit
        self._inject_desc_max = inject_desc_max
        self._llm_max_tokens = llm_max_tokens
        self._converse_modes = converse_modes
        self._hooks = hooks

    def normalize_converse_mode(self, raw: Any) -> str:
        mode = str(raw or "fast").strip().lower()
        if mode in ("deep", "long", "long_context", "long-context"):
            return "deep"
        if mode in ("raw", "plain", "user_only", "user-only", "no_inject", "no-inject"):
            return "raw"
        return "fast" if mode in self._converse_modes else "fast"

    def converse_mode_profile(self, mode: Any) -> Dict[str, Any]:
        mode = self.normalize_converse_mode(mode)
        if mode == "deep":
            deep_ctx = os.environ.get("CNEXUS_DEEP_NUM_CTX", "16384").strip()
            try:
                num_ctx = int(deep_ctx)
            except ValueError:
                num_ctx = 16384
            deep_tokens = os.environ.get("CNEXUS_DEEP_MAX_TOKENS", "4096").strip()
            try:
                llm_max = int(deep_tokens)
            except ValueError:
                llm_max = 4096
            return {
                "mode": "deep",
                "inject_limit": max(1, int(os.environ.get("CNEXUS_DEEP_INJECT_LIMIT", "8"))),
                "inject_desc_max": max(40, int(os.environ.get("CNEXUS_DEEP_INJECT_DESC_MAX", "320"))),
                "llm_max_tokens": llm_max,
                "num_ctx": num_ctx,
                "inject_memory": True,
                "activation_threshold": self._activation_threshold * 0.85,
                "use_recall_supplement": True,
            }
        if mode == "raw":
            return {
                "mode": "raw",
                "inject_limit": 0,
                "inject_desc_max": 0,
                "llm_max_tokens": self._llm_max_tokens,
                "num_ctx": None,
                "inject_memory": False,
                "activation_threshold": self._activation_threshold,
                "use_recall_supplement": False,
            }
        return {
            "mode": "fast",
            "inject_limit": self._inject_limit if self._inject_limit > 0 else 2,
            "inject_desc_max": self._inject_desc_max,
            "llm_max_tokens": self._llm_max_tokens,
            "num_ctx": None,
            "inject_memory": True,
            "activation_threshold": self._activation_threshold,
            "use_recall_supplement": False,
        }

    def normalize_thinking_mode(self, raw: Any) -> str:
        return normalize_thinking_mode(raw)

    def thinking_inference_params(self, thinking_mode: str = "precision") -> Dict[str, Any]:
        mode = normalize_thinking_mode(thinking_mode)
        return thinking_inference_params(mode, self._hooks.global_entropy_int())

    def parse_request_modes(self, data: Optional[dict]) -> Tuple[str, str]:
        payload = data or {}
        raw_mode = str(payload.get("mode") or "").strip().lower()
        thinking_mode = payload.get("thinking_mode")
        converse_mode = payload.get("converse_mode")
        if thinking_mode is None and raw_mode in ("precision", "emergent"):
            thinking_mode = raw_mode
        if converse_mode is None and raw_mode in self._converse_modes:
            converse_mode = raw_mode
        return (
            self.normalize_converse_mode(converse_mode or "fast"),
            self.normalize_thinking_mode(thinking_mode or "precision"),
        )

    def parse_memory_scope(self, data: Optional[dict]) -> str:
        from .memory.scope import normalize_memory_scope

        payload = data or {}
        raw = payload.get("memory_scope")
        if raw is None:
            raw = payload.get("recall_scope")
        if raw is None:
            raw = payload.get("scope")
        return normalize_memory_scope(raw)
