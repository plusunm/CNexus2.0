"""Memory clear control API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class MemoryControlHooks:
    audit_event: Callable[..., None]
    get_current_model_registry: Callable[[], Dict[str, Any]]
    default_model_registry: Callable[[], Dict[str, Any]]
    reset_engine_memory: Callable[[Dict[str, Any]], None]
    persist_file_path: Callable[[], str]
    append_runtime_log: Callable[..., None]
    persist_engine_state: Callable[[], None]
    persistence_status: Callable[[], Dict[str, Any]]


class MemoryControlService:
    def __init__(self, hooks: MemoryControlHooks):
        self._hooks = hooks

    def clear(self, *, keep_models: bool = True) -> Dict[str, Any]:
        self._hooks.audit_event("memory.clear", {"keep_models": bool(keep_models)})
        registry = (
            dict(self._hooks.get_current_model_registry())
            if keep_models
            else self._hooks.default_model_registry()
        )
        self._hooks.reset_engine_memory(registry)
        path = self._hooks.persist_file_path()
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError as exc:
            self._hooks.append_runtime_log(
                f"删除快照文件失败 · {exc}",
                category="control_plane",
                level="warn",
            )
        self._hooks.persist_engine_state()
        self._hooks.append_runtime_log("记忆已手动清空", category="control_plane")
        return {
            "ok": True,
            "cleared": True,
            "keep_models": bool(keep_models),
            "persistence": self._hooks.persistence_status(),
        }
