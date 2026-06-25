"""REM deep-sleep control API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class RemControlHooks:
    run_rem_deep_sleep: Callable[..., Dict[str, Any]]


class RemControlService:
    def __init__(self, hooks: RemControlHooks):
        self._hooks = hooks

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        force = bool(data.get("force"))
        return self._hooks.run_rem_deep_sleep(force=force)
