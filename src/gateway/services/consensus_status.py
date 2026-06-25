"""Negotiation + reputation consensus status for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class ConsensusStatusHooks:
    get_negotiation_manager: Callable[[], Any]
    get_reputation_registry: Callable[[], Any]


class ConsensusStatusService:
    def __init__(self, hooks: ConsensusStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        neg = self._hooks.get_negotiation_manager()
        rep = self._hooks.get_reputation_registry()
        return {
            "negotiation": neg.status() if neg else {"enabled": False},
            "reputation_peers": len(rep.get_all()) if rep else 0,
        }
