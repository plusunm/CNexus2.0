"""Self-reflection engine status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class ReflectionStatusHooks:
    reflection_engine_status: Callable[[], Dict[str, Any]]


class ReflectionStatusService:
    def __init__(self, hooks: ReflectionStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        return self._hooks.reflection_engine_status()
