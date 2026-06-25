"""Static /v1 probe responses derived from engine state."""

from __future__ import annotations

import time
from typing import Any, Dict

from ..state import EngineStateManager


class SystemProbeService:
    """Gateway-owned health + capability probes — no app_v2 imports."""

    def __init__(self, state: EngineStateManager):
        self._state = state

    def gateway_health(self) -> Dict[str, Any]:
        return {
            "gateway": "alive",
            "operational_ready": True,
            "full_ready": True,
            "boot_phase": "boot_4_ready",
            "cognitive_status": "ready",
            "progress": 100,
            "reachable": True,
            "booted": True,
            "version": "2.0.0-personal",
            "status": "ok",
        }

    def system_capability(self) -> Dict[str, Any]:
        return {
            "api": True,
            "chat": True,
            "memory": True,
            "llm": True,
            "upload": True,
            "full": True,
            "operational_ready": True,
            "full_ready": True,
            "ready_for_chat": True,
            "ready_for_upload": True,
            "status": "ready",
        }

    def system_ready(self) -> Dict[str, Any]:
        started_at = float(self._state.get("started_at") or time.time())
        return {
            "status": "ready",
            "boot_id": "personal-static",
            "boot_phase": "boot_4_ready",
            "token_valid": True,
            "ws": "disabled",
            "http": "alive",
            "memory": "ready",
            "uptime_ms": int((time.time() - started_at) * 1000),
            "version": "2.0.0-personal",
            "operational_ready": True,
            "full_ready": True,
            "ready_for_chat": True,
            "ready_for_upload": True,
            "ready": True,
        }

    def memory_stats(self) -> Dict[str, Any]:
        def _count(engine):
            return len(engine["memory_store"].blocks)

        total = self._state.mutate(_count)
        return {"total": total, "by_layer": {"episodic": total}, "avg_importance": 0.6}
