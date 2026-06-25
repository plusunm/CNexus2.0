"""REM consolidation status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from ..state import EngineStateManager


@dataclass(frozen=True)
class ConsolidationStatusHooks:
    rem_consolidation_status: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
    build_rem_context: Callable[[], Dict[str, Any]]


class ConsolidationStatusService:
    def __init__(self, state: EngineStateManager, hooks: ConsolidationStatusHooks):
        self._state = state
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        consolidation = self._state.mutate(
            lambda engine: engine.setdefault("consolidation", {})
        )
        ctx = self._hooks.build_rem_context()
        base = self._hooks.rem_consolidation_status(consolidation, ctx)
        semantic_facts = self._state.mutate(_count_semantic_facts)
        base["semantic_facts"] = semantic_facts
        base["last_shallow_at"] = consolidation.get("last_shallow_at")
        return base


def _count_semantic_facts(engine: Dict[str, Any]) -> int:
    return sum(
        1
        for block in engine["memory_store"].blocks
        if block.get("label") == "semantic" or str(block.get("block_id", "")).startswith("sem-rem-")
    )
