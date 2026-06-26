"""Application control surface — unified semantic state machine (P5.3)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

PHASE_IDLE = "idle"
PHASE_CONNECTED = "connected"
PHASE_DIAGNOSED = "diagnosed"
PHASE_GATE_PREVIEW = "gate_preview"
PHASE_REPAIR_PENDING = "repair_pending"
PHASE_REPAIR_COMPLETE = "repair_complete"
PHASE_PUBLISHED = "published"

VALID_PHASES = frozenset({
    PHASE_IDLE,
    PHASE_CONNECTED,
    PHASE_DIAGNOSED,
    PHASE_GATE_PREVIEW,
    PHASE_REPAIR_PENDING,
    PHASE_REPAIR_COMPLETE,
    PHASE_PUBLISHED,
})


@dataclass
class ApplicationControlState:
    """
    Tracks the human-in-the-loop control surface across connect → hook → gate → execute.
    Not persisted — session-scoped observability for UI and API consumers.
    """

    phase: str = PHASE_IDLE
    peer_id: str = ""
    peer_host: str = ""
    last_hook: Dict[str, Any] = field(default_factory=dict)
    last_gate: Dict[str, Any] = field(default_factory=dict)
    last_connect: Dict[str, Any] = field(default_factory=dict)
    last_publish: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def transition(self, phase: str, **ctx: Any) -> None:
        if phase not in VALID_PHASES:
            raise ValueError(f"invalid application phase: {phase}")
        self.phase = phase
        self.updated_at = time.time()
        for key, value in ctx.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def absorb_connect(self, report: Dict[str, Any]) -> None:
        """Update control state from a connectivity_connect report."""
        self.last_connect = dict(report or {})
        peer_id = str(report.get("peer_id") or report.get("pubkey") or "")
        peer_host = str(report.get("url") or report.get("host") or "")
        hook = dict(report.get("repair_hook") or {})
        self.last_hook = hook
        if peer_id:
            self.peer_id = peer_id
        if peer_host:
            self.peer_host = peer_host

        if not report.get("ok"):
            self.transition(PHASE_IDLE, peer_id=peer_id, peer_host=peer_host)
            return

        missing = int(hook.get("missing_count") or 0)
        gate = dict(hook.get("execution_gate") or {})
        if gate:
            self.last_gate = gate
            self.transition(
                PHASE_GATE_PREVIEW if missing > 0 else PHASE_CONNECTED,
                peer_id=peer_id,
                peer_host=peer_host,
            )
        elif missing > 0:
            self.transition(PHASE_DIAGNOSED, peer_id=peer_id, peer_host=peer_host)
        else:
            self.transition(PHASE_CONNECTED, peer_id=peer_id, peer_host=peer_host)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "peer_id": self.peer_id,
            "peer_host": self.peer_host,
            "updated_at": self.updated_at,
            "has_hook": bool(self.last_hook),
            "has_gate": bool(self.last_gate),
            "missing_count": int(self.last_hook.get("missing_count") or 0),
            "plan_count": int(self.last_hook.get("plan_count") or 0),
        }
