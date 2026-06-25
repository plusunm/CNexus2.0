"""Self-reflection meta control API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class ReflectionControlHooks:
    run_self_reflection: Callable[..., Dict[str, Any]]


class ReflectionControlService:
    def __init__(self, hooks: ReflectionControlHooks):
        self._hooks = hooks

    def reflect_meta(self, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = data or {}
        question = str(payload.get("question") or payload.get("q") or "").strip() or None
        try:
            limit = int(payload.get("limit")) if payload.get("limit") is not None else None
        except (TypeError, ValueError):
            limit = None
        try:
            window_days = int(payload.get("window_days")) if payload.get("window_days") is not None else None
        except (TypeError, ValueError):
            window_days = None
        use_llm = payload.get("use_llm", True)
        if isinstance(use_llm, str):
            use_llm = use_llm.lower() not in ("0", "false", "no")
        return self._hooks.run_self_reflection(
            question=question,
            limit=limit,
            window_days=window_days,
            use_llm=bool(use_llm),
        )
