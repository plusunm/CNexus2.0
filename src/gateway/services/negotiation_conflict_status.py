"""Negotiation conflict buffer status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from ..state import EngineStateManager


@dataclass(frozen=True)
class NegotiationConflictStatusHooks:
    negotiation_conflict_enabled: Callable[[], bool]
    negotiation_conflict_use_llm: Callable[[], bool]
    negotiation_conflict_context: Callable[[], str]


class NegotiationConflictStatusService:
    def __init__(self, state: EngineStateManager, hooks: NegotiationConflictStatusHooks):
        self._state = state
        self._hooks = hooks

    def build_recent(self) -> Dict[str, Any]:
        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            raw_items = list(engine.get("negotiation_conflicts") or [])[:8]
            items = [_normalize_negotiation_item(row, index) for index, row in enumerate(raw_items)]
            return {
                "enabled": self._hooks.negotiation_conflict_enabled(),
                "llm_auto_resolve": self._hooks.negotiation_conflict_use_llm(),
                "count": len(engine.get("negotiation_conflicts") or []),
                "items": items,
                "context_preview": self._hooks.negotiation_conflict_context()[:1200],
            }

        return self._state.mutate(_read)


def _normalize_negotiation_item(row: Any, index: int) -> Dict[str, Any]:
    item = dict(row or {})
    if not item.get("id"):
        item["id"] = f"neg-{int(item.get('at') or 0)}-{index}"
    if not item.get("pairs") and item.get("resolutions"):
        item["pairs"] = [
            {
                "block_id": str(res.get("block_id") or ""),
                "local": {"content": "", "label": "episode"},
                "remote": {"content": "", "label": "episode"},
                "resolution": {
                    "status": res.get("status"),
                    "merged_content": res.get("merged_content"),
                    "fork": res.get("fork"),
                    "rationale": res.get("rationale"),
                    "source": res.get("source"),
                    "temperature": res.get("temperature"),
                    "global_entropy": res.get("global_entropy"),
                },
            }
            for res in item.get("resolutions") or []
        ]
    return item
