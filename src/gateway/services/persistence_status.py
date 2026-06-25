"""Persistence file status fragment for L0 snapshot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict

from ..state import EngineStateManager


@dataclass(frozen=True)
class PersistenceStatusHooks:
    persist_version: str
    persist_file_path: Callable[[], str]
    persist_meta: Callable[[], Dict[str, Any]]


class PersistenceStatusService:
    def __init__(self, state: EngineStateManager, hooks: PersistenceStatusHooks):
        self._state = state
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        meta = self._hooks.persist_meta()
        path = self._hooks.persist_file_path()

        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "enabled": True,
                "version": self._hooks.persist_version,
                "path": path,
                "exists": os.path.isfile(path),
                "saved_at": meta.get("saved_at"),
                "loaded_at": meta.get("loaded_at"),
                "memory_blocks": len(engine["memory_store"].blocks),
                "trace_count": len(engine.get("trace", [])),
                "projection_nodes": len(engine.get("projection", {}).get("nodes", {})),
            }

        return self._state.mutate(_read)
