"""Thread-safe wrapper around the runtime engine state dict."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class EngineStateManager:
    """Serializes reads/writes to the shared engine state mapping."""

    def __init__(self, state: Dict[str, Any]):
        self._state = state
        self._lock = threading.RLock()

    @property
    def raw(self) -> Dict[str, Any]:
        return self._state

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value

    def mutate(self, fn: Callable[[Dict[str, Any]], T]) -> T:
        with self._lock:
            return fn(self._state)

    def model_registry(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            reg = self._state.setdefault("model_registry", {})
            return reg

    def mutate_model_registry(self, fn: Callable[[Dict[str, Dict[str, Any]]], T]) -> T:
        with self._lock:
            reg = self._state.setdefault("model_registry", {})
            return fn(reg)

    def get_model_row(self, model_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            reg = self._state.get("model_registry") or {}
            row = reg.get(model_id)
            return dict(row) if row else None

    def mutate_memory_store(self, fn: Callable[[Any], T]) -> T:
        with self._lock:
            store = self._state["memory_store"]
            return fn(store)

    def extend_gtbs_events(self, rows: list) -> None:
        with self._lock:
            events = self._state.setdefault("gtbs_events", [])
            events.extend(rows)
            if len(events) > 2000:
                self._state["gtbs_events"] = events[-2000:]

    def append_runtime_log(self, entry: Dict[str, Any]) -> None:
        with self._lock:
            logs = self._state.setdefault("runtime_logs", [])
            logs.append(entry)
            if len(logs) > 500:
                self._state["runtime_logs"] = logs[-500:]

    def touch_consolidation_activity(self) -> None:
        with self._lock:
            consolidation = self._state.setdefault("consolidation", {})
            consolidation["last_activity_at"] = time.time()
