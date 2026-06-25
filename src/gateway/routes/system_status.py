"""GET routes for status, shadow /v1 probes, and observability."""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs

from ..http.responses import HttpRouteResponse
from ..services.dashboard_status import DashboardStatusService
from ..services.gateway_intent import GatewayIntentService
from ..services.memory_recall import MemoryRecallService
from ..services.network_status import NetworkStatusService
from ..services.peers_status import PeersStatusService
from ..services.shadow_projection import ShadowProjectionService
from ..services.status_snapshot import StatusSnapshotService
from ..services.status_subsystems import StatusSubsystemsService
from ..services.system_probe import SystemProbeService


class SystemStatusRouteHandler:
    """Status + shadow read APIs — returns None when path is not handled."""

    def __init__(
        self,
        probe: SystemProbeService,
        subsystems: StatusSubsystemsService,
        snapshot: StatusSnapshotService,
        dashboard: DashboardStatusService,
        peers: PeersStatusService,
        network: NetworkStatusService,
        shadow: ShadowProjectionService,
        memory_recall: MemoryRecallService,
        gateway_intent: GatewayIntentService | None = None,
    ):
        self._probe = probe
        self._subsystems = subsystems
        self._snapshot = snapshot
        self._dashboard = dashboard
        self._peers = peers
        self._network = network
        self._shadow = shadow
        self._memory_recall = memory_recall
        self._gateway_intent = gateway_intent

    def handle_get(self, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        qs = parse_qs(query or "")

        if path == "/api/status":
            return HttpRouteResponse.json(self._snapshot.build())

        if path in ("/api/dashboard/status", "/api/metrics"):
            payload = self._dashboard.build()
            status = 503 if payload.get("ok") is False and payload.get("error") else 200
            return HttpRouteResponse.json(payload, status)

        if path == "/api/replay/status":
            return HttpRouteResponse.json({"ok": True, **self._subsystems.replay_status()})

        if path == "/api/awakening/status":
            return HttpRouteResponse.json({"ok": True, "awakening": self._subsystems.awakening_status()})

        if path == "/api/reflect/status":
            return HttpRouteResponse.json({"ok": True, "reflection": self._subsystems.reflection_status()})

        if path == "/api/conflict/status":
            return HttpRouteResponse.json(
                {"ok": True, "conflict_resolution": self._subsystems.conflict_resolution_status()}
            )

        if path == "/api/conflict/negotiation":
            return HttpRouteResponse.json(
                {"ok": True, "negotiation_conflicts": self._subsystems.negotiation_conflict_recent()}
            )

        if path == "/api/pruning/status":
            return HttpRouteResponse.json({"ok": True, "pruning": self._subsystems.pruning_status()})

        if path == "/api/entropy/status":
            return HttpRouteResponse.json({"ok": True, "entropy": self._subsystems.entropy_status()})

        if path == "/api/peers":
            return HttpRouteResponse.json({"ok": True, **self._peers.build()})

        if path == "/api/connectivity/status":
            return HttpRouteResponse.json({"ok": True, "network": self._network.build()})

        if path == "/api/dht/status":
            return HttpRouteResponse.json({"ok": True, "dht": self._network.dht_status()})

        if path == "/v1/gateway/health":
            return HttpRouteResponse.json(self._probe.gateway_health())

        if path == "/v1/gateway/state":
            return HttpRouteResponse.json(self._probe.gateway_health())

        if path == "/v1/system/capability":
            return HttpRouteResponse.json(self._probe.system_capability())

        if path in ("/v1/system/ready", "/v1/system/ready/stream"):
            return HttpRouteResponse.json(self._probe.system_ready())

        if path == "/v1/health":
            return HttpRouteResponse.json({"status": "ok", "service": "cnexus-2.0-personal"})

        if path == "/health":
            return HttpRouteResponse.json(
                {
                    "status": "ok",
                    "service": "cnexus-2.0-personal",
                    "cnexus": True,
                    "operational_ready": True,
                    "full_ready": True,
                }
            )

        if path == "/v1/memory/stats":
            return HttpRouteResponse.json(self._probe.memory_stats())

        if path == "/v1/execution/status":
            return HttpRouteResponse.json(self._shadow.execution_status())

        if path == "/v1/ollama/status":
            return HttpRouteResponse.json(self._shadow.ollama_status())

        if path.startswith("/logs"):
            limit = int(qs.get("limit", ["100"])[0] or 100)
            return HttpRouteResponse.json(self._shadow.api_logs(limit))

        if path.startswith("/v1/gtbs/events"):
            limit = int(qs.get("limit", ["300"])[0] or 300)
            return HttpRouteResponse.json(self._shadow.gtbs_events(limit))

        if path == "/v1/cse/live":
            window = int(qs.get("window", ["200"])[0] or 200)
            return HttpRouteResponse.json(self._shadow.cse_live(window))

        if path == "/v1/spine/token/observatory":
            limit = int(qs.get("limit", ["100"])[0] or 100)
            return HttpRouteResponse.json(self._shadow.token_observatory(limit))

        if path == "/v1/runtime/introspect":
            return HttpRouteResponse.json(self._shadow.runtime_introspect())

        if path.startswith("/v1/spine/token/trace/"):
            trace_id = path[len("/v1/spine/token/trace/") :]
            return HttpRouteResponse.json(self._shadow.token_field(trace_id))

        if path == "/v1/kernel/records/recent":
            limit = int(qs.get("limit", ["20"])[0] or 20)
            return HttpRouteResponse.json(self._shadow.kernel_records_recent(limit))

        if path.startswith("/v1/kernel/record/"):
            rest = path[len("/v1/kernel/record/") :]
            if rest.endswith("/learn"):
                trace_id = rest[: -len("/learn")]
                payload = self._shadow.kernel_learn(trace_id)
                if payload is None:
                    return HttpRouteResponse.json({"detail": f"record not found: {trace_id}"}, 404)
                return HttpRouteResponse.json(payload)
            trace_id = rest
            payload = self._shadow.kernel_record(trace_id)
            if payload is None:
                return HttpRouteResponse.json({"detail": f"record not found: {trace_id}"}, 404)
            return HttpRouteResponse.json(payload)

        if path == "/v1/memory/recall":
            recall_query = qs.get("query", [""])[0] or ""
            return HttpRouteResponse.json(self._memory_recall.recall(recall_query))

        if path in ("/v1/system/compute", "/v1/mind/overview"):
            return HttpRouteResponse.json(self._snapshot.build())

        if path.startswith("/v1/gateway/intent/") and path != "/v1/gateway/intent":
            trace_id = path.rsplit("/", 1)[-1]
            if self._gateway_intent is not None:
                job = self._gateway_intent.get_job(trace_id)
                if job:
                    return HttpRouteResponse.json(job)
            return HttpRouteResponse.json(
                {
                    "trace_id": trace_id,
                    "status": "queued",
                    "ok": True,
                }
            )

        if path.startswith("/v1/gateway/") or path.startswith("/v1/"):
            return HttpRouteResponse.json(
                {"status": "ok", "ok": True, "message": "L0 fallback - WS/L3 not available"}
            )

        return None
