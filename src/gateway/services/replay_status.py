"""Log replay status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from ..state import EngineStateManager

_REPLAYABLE_EVENT_KEYS = ("memory.block", "trace.cycle", "asset.upload", "asset.received")


@dataclass(frozen=True)
class ReplayStatusHooks:
    get_log_replay_engine: Callable[[], Any]
    get_audit_log: Callable[[], Any]
    get_state_reconstructor: Callable[[], Any]


class ReplayStatusService:
    def __init__(self, state: EngineStateManager, hooks: ReplayStatusHooks):
        self._state = state
        self._hooks = hooks

    def build(self, awakening_status: Dict[str, Any]) -> Dict[str, Any]:
        engine = self._hooks.get_log_replay_engine()
        if engine is None:
            return {"enabled": False}
        audit = self._hooks.get_audit_log()
        counts = engine.count_replayable_events()
        replayable = sum(counts.get(key, 0) for key in _REPLAYABLE_EVENT_KEYS)

        def _counts(engine_state: Dict[str, Any]) -> tuple[int, int]:
            return len(engine_state["memory_store"].blocks), len(engine_state.get("trace", []))

        memory_blocks, trace_count = self._state.mutate(_counts)
        status = dict(engine.status())
        status["needed"] = engine.replay_needed(
            audit_entry_count=audit.entry_count() if audit else 0,
            memory_block_count=memory_blocks,
            trace_count=trace_count,
            replayable_in_audit=replayable,
        )
        recon = self._hooks.get_state_reconstructor()
        if recon is not None:
            status["reconstructor"] = recon.status()
        status["awakening"] = awakening_status
        return status
