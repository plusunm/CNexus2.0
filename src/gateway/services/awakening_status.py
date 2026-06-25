"""Awakening / genesis / reconstructor status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class AwakeningStatusHooks:
    read_awakening_base: Callable[[], Dict[str, Any]]
    genesis_status: Callable[[], Dict[str, Any]]
    reconstructor_status: Callable[[], Dict[str, Any]]


class AwakeningStatusService:
    def __init__(self, hooks: AwakeningStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        genesis_status = self._hooks.genesis_status()
        recon_status = self._hooks.reconstructor_status()
        base = dict(self._hooks.read_awakening_base())
        bootstrap_at = genesis_status.get("last_bootstrap_at")
        peer_results = genesis_status.get("peer_results") or {}
        genesis_running = bool(bootstrap_at) and base.get("phase") not in (
            "alive",
            "idle",
            "replay",
            "vector_index",
        )
        if base.get("phase") == "idle" and bootstrap_at and not base.get("completed_at"):
            aligned = sum(1 for row in peer_results.values() if row.get("aligned"))
            total = max(1, len(peer_results))
            if aligned < total:
                base.update(
                    {
                        "phase": "genesis",
                        "label": "genesis",
                        "progress": min(0.95, aligned / total),
                        "message": f"基因同步 {aligned}/{total} 节点已对齐",
                        "alive": False,
                    }
                )
        if recon_status.get("progress"):
            prog = recon_status["progress"]
            if prog.get("phase") in ("replay", "vector_index", "alive"):
                base.update(
                    {
                        "phase": prog.get("phase"),
                        "label": prog.get("phase"),
                        "progress": prog.get("progress", base.get("progress", 0)),
                        "message": prog.get("message", base.get("message", "")),
                        "started_at": prog.get("started_at", base.get("started_at")),
                        "completed_at": prog.get("completed_at", base.get("completed_at")),
                        "alive": prog.get("phase") == "alive",
                    }
                )
        last_report = recon_status.get("last_report") or {}
        return {
            "phase": base.get("phase", "idle"),
            "label": base.get("label", "idle"),
            "progress": base.get("progress", 0.0),
            "message": base.get("message", ""),
            "started_at": base.get("started_at"),
            "completed_at": base.get("completed_at"),
            "alive": bool(base.get("alive", True)),
            "genesis": {
                "enabled": genesis_status.get("enabled", False),
                "bootstrap_at": bootstrap_at,
                "full_sync_peers": genesis_status.get("full_sync_peers", 0),
                "running": genesis_running,
            },
            "replay": recon_status,
            "summary": last_report.get("summary"),
            "last_report": last_report,
        }
