"""Conflict resolution agent + negotiation flags status fragment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from ..state import EngineStateManager


@dataclass(frozen=True)
class ConflictResolutionStatusHooks:
    conflict_agent_status: Callable[[], Dict[str, Any]]
    negotiation_conflict_enabled: Callable[[], bool]
    negotiation_conflict_use_llm: Callable[[], bool]


class ConflictResolutionStatusService:
    def __init__(self, state: EngineStateManager, hooks: ConflictResolutionStatusHooks):
        self._state = state
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        agent_base = self._hooks.conflict_agent_status()

        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            flags = engine.get("runtime_flags") or {}
            return {
                **agent_base,
                "negotiation_conflict_enabled": self._hooks.negotiation_conflict_enabled(),
                "negotiation_conflict_buffer": len(engine.get("negotiation_conflicts") or []),
                "negotiation_conflict_llm": self._hooks.negotiation_conflict_use_llm(),
                "negotiation_conflict_llm_runtime": "negotiation_conflict_llm" in flags,
                "negotiation_conflict_enabled_runtime": "negotiation_conflict_enabled" in flags,
            }

        return self._state.mutate(_read)
