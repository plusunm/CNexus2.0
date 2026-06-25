"""Cognitive pruning control APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

JsonResponse = Tuple[Any, int]


@dataclass(frozen=True)
class PruningControlHooks:
    get_pruning_engine: Callable[[], Any]


class PruningControlService:
    def __init__(self, hooks: PruningControlHooks):
        self._hooks = hooks

    def run(self, data: Dict[str, Any] | None = None) -> JsonResponse:
        engine = self._hooks.get_pruning_engine()
        if engine is None:
            return {"ok": False, "error": "pruning_unavailable"}, 503
        dry_run = bool((data or {}).get("dry_run"))
        report = engine.run_cycle(dry_run=dry_run)
        code = 200 if report.get("ok") else 400
        return {"ok": report.get("ok", False), "report": report, "status": engine.status()}, code
