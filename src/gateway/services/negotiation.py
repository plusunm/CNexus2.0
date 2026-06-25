"""Negotiation conflict buffer → converse emergent injection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List

from ..state import EngineStateManager


def _format_resolution_snippet(resolution: dict) -> str:
    status = str(resolution.get("status") or "")
    if status == "merged":
        text = str(resolution.get("merged_content") or "").strip()
        return f"[merged] {text[:320]}"
    if status == "forked":
        fork = dict(resolution.get("fork") or {})
        return (
            f"[forked] local: {str(fork.get('local') or '')[:160]} | "
            f"remote: {str(fork.get('remote') or '')[:160]}"
        )
    if status == "aligned":
        return f"[aligned] {str(resolution.get('merged_content') or '')[:160]}"
    return f"[{status}] {str(resolution.get('rationale') or '')[:160]}"


def format_negotiation_conflict_context(buffer: list, *, limit: int = 3) -> str:
    if not buffer:
        return ""
    lines = ["--- Recent negotiation conflicts (cross-node synthesis) ---"]
    shown = 0
    for item in buffer[:limit]:
        peer = str(item.get("peer_pubkey") or "peer")[:16]
        err = str(item.get("negotiation_error") or "negotiation_failed")
        entropy = str(item.get("global_entropy") or "")
        if entropy:
            lines.append(f"Peer {peer} · {err} · entropy {entropy}")
        else:
            lines.append(f"Peer {peer} · {err}")
        for resolution in item.get("resolutions") or []:
            lines.append(_format_resolution_snippet(resolution))
            shown += 1
            if shown >= limit * 2:
                break
        if shown >= limit * 2:
            break
    return "\n".join(lines) if len(lines) > 1 else ""


GetPruningEngineFn = Callable[[], Any]


@dataclass(frozen=True)
class NegotiationHooks:
    get_cognitive_pruning_engine: GetPruningEngineFn


class NegotiationService:
    """Format negotiation conflicts and record emergent block refs — no app_v2 imports."""

    def __init__(self, state: EngineStateManager, hooks: NegotiationHooks):
        self._state = state
        self._hooks = hooks

    def conflict_context(self) -> str:
        try:
            buffer = self._state.get("negotiation_conflicts") or []
            return format_negotiation_conflict_context(buffer) or ""
        except Exception:
            return ""

    def record_emergent_block_refs(self) -> None:
        prune = self._hooks.get_cognitive_pruning_engine()
        if prune is None:
            return

        def _record(engine):
            for row in engine.get("negotiation_conflicts") or []:
                for pair in row.get("pairs") or []:
                    block_id = str(pair.get("block_id") or "")
                    if block_id:
                        prune.record_block_reference(block_id)
            return None

        self._state.mutate(_record)
