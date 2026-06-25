"""Short-lived circuit breaker for external LLM providers."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional


def _cooldown_seconds() -> float:
    raw = os.environ.get("CNEXUS_LLM_FAILURE_COOLDOWN", "90").strip()
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 90.0


class ProviderHealthGate:
    """Skip unreachable providers for a cooldown window after a failed call."""

    def __init__(self, cooldown_seconds: Optional[float] = None):
        self._cooldown = cooldown_seconds if cooldown_seconds is not None else _cooldown_seconds()
        self._until: Dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def provider_key(model_row: Any) -> str:
        if not model_row:
            return ""
        provider = str(model_row.get("provider") or "")
        model_id = str(model_row.get("id") or model_row.get("model") or "")
        return f"{provider}:{model_id}"

    def allow(self, model_row: Any) -> bool:
        key = self.provider_key(model_row)
        if not key:
            return True
        now = time.time()
        with self._lock:
            until = self._until.get(key, 0.0)
            if until > now:
                return False
            if until:
                self._until.pop(key, None)
            return True

    def record_success(self, model_row: Any) -> None:
        key = self.provider_key(model_row)
        if not key:
            return
        with self._lock:
            self._until.pop(key, None)

    def record_failure(self, model_row: Any) -> None:
        key = self.provider_key(model_row)
        if not key:
            return
        with self._lock:
            self._until[key] = time.time() + self._cooldown
