"""Log replay control API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class ReplayControlHooks:
    run_log_replay: Callable[..., Dict[str, Any]]


class ReplayControlService:
    def __init__(self, hooks: ReplayControlHooks):
        self._hooks = hooks

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        force = bool(data.get("force"))
        return self._hooks.run_log_replay(force=force, reset=True)
