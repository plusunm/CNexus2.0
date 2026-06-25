"""Network resilience score for L0 mind overview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from .audit_chain_status import AuditChainStatusService


@dataclass(frozen=True)
class ResilienceStatusHooks:
    get_metrics_module: Callable[[], Any]
    get_gossip_sync: Callable[[], Any]
    get_peer_registry: Callable[[], Any]
    heartbeat_stale_seconds: Callable[[], float]


class ResilienceStatusService:
    """Compute mesh resilience from metrics + gossip health."""

    def __init__(self, hooks: ResilienceStatusHooks, audit: AuditChainStatusService):
        self._hooks = hooks
        self._audit = audit

    def build(self) -> Dict[str, Any]:
        metrics = self._hooks.get_metrics_module()
        gossip = self._hooks.get_gossip_sync()
        if not metrics or not gossip:
            return {"score": 1.0, "label": "solo", "total_nodes": 1, "full_sync_nodes": 1}

        reg = self._hooks.get_peer_registry()
        gossip_health = metrics.gossip_health_from_sync(
            gossip,
            reg,
            stale_seconds=self._hooks.heartbeat_stale_seconds(),
        )
        return metrics.build_resilience(
            gossip_health.get("peers") or [],
            self._audit.build(),
            gossip_health,
        )
