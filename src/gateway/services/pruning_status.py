"""Cognitive pruning status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class PruningStatusHooks:
    get_cognitive_pruning_engine: Callable[[], Any]


class PruningStatusService:
    def __init__(self, hooks: PruningStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        engine = self._hooks.get_cognitive_pruning_engine()
        if engine is None:
            return {"enabled": False, "error": "pruning_unavailable"}
        return engine.status()
