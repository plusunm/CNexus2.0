"""Mission Control dashboard payload — /api/dashboard/status and /api/metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ..state import EngineStateManager
from .audit_chain_status import AuditChainStatusService
from .consensus_status import ConsensusStatusService
from .identity_status import IdentityStatusService
from .status_subsystems import StatusSubsystemsService


@dataclass(frozen=True)
class DashboardStatusHooks:
    get_metrics_module: Callable[[], Any]
    get_audit_log: Callable[[], Any]
    get_gossip_sync: Callable[[], Any]
    get_peer_registry: Callable[[], Any]
    heartbeat_stale_seconds: Callable[[], float]
    server_port: int


class DashboardStatusService:
    """Assemble dashboard JSON from metrics module + engine/subsystem snapshots."""

    def __init__(
        self,
        state: EngineStateManager,
        subsystems: StatusSubsystemsService,
        identity: IdentityStatusService,
        audit: AuditChainStatusService,
        consensus: ConsensusStatusService,
        hooks: DashboardStatusHooks,
    ):
        self._state = state
        self._subsystems = subsystems
        self._identity = identity
        self._audit = audit
        self._consensus = consensus
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        metrics = self._hooks.get_metrics_module()
        if not metrics:
            return {"ok": False, "error": "metrics_unavailable"}

        audit = self._hooks.get_audit_log()
        identity = self._identity.build()
        audit_view = dict(self._audit.build())
        if audit is not None:
            audit_view["last_hash_full"] = audit.last_hash

        gossip = self._hooks.get_gossip_sync()
        reg = self._hooks.get_peer_registry()
        gossip_health = metrics.gossip_health_from_sync(
            gossip,
            reg,
            stale_seconds=self._hooks.heartbeat_stale_seconds(),
        )
        node_id = identity.get("pubkey") or "cnexus-local"

        def _engine_counts(engine: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "started_at": float(engine.get("started_at", time.time())),
                "memory_count": len(engine["memory_store"].blocks),
                "trace_count": len(engine.get("trace", [])),
                "current_iteration": engine.get("current_iteration", 0),
            }

        counts = self._state.mutate(_engine_counts)
        uptime = time.time() - counts["started_at"]

        return metrics.build_dashboard_status(
            node_id=node_id,
            uptime_seconds=uptime,
            resources=metrics.collect_system_resources(),
            identity=identity,
            audit=audit_view,
            peers_registry=reg.get_all_peers() if reg else {},
            gossip_health=gossip_health,
            engine={
                "memory_count": counts["memory_count"],
                "trace_count": counts["trace_count"],
                "current_iteration": counts["current_iteration"],
            },
            rem_status=self._subsystems.consolidation_status(),
            consensus_status=self._consensus.build(),
            replay_status=self._subsystems.replay_status(),
            awakening_status=self._subsystems.awakening_status(),
            reflection_status=self._subsystems.reflection_status(),
            conflict_resolution_status=self._subsystems.conflict_resolution_status(),
            pruning_status=self._subsystems.pruning_status(),
            entropy_status=self._subsystems.entropy_status(),
            port=self._hooks.server_port,
        )
