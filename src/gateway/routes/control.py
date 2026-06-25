"""Control-plane POST routes — memory, replay, conflict, pruning, ollama."""

from __future__ import annotations

from typing import Any, Optional

from ..http.responses import HttpRouteResponse
from ..services.control_plane import ControlPlaneService
from ..services.gateway_intent import GatewayIntentService
from ..services.status_snapshot import StatusSnapshotService


class ControlRouteHandler:
    """Cognitive control APIs — returns None when path is not handled."""

    def __init__(
        self,
        control: ControlPlaneService,
        snapshot: StatusSnapshotService,
        gateway_intent: GatewayIntentService,
    ):
        self._control = control
        self._snapshot = snapshot
        self._gateway_intent = gateway_intent

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path in ("/api/memory/clear", "/v1/memory/clear"):
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.memory_clear(data))

        if path == "/v1/memory/rem-sleep":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.rem_sleep(data))

        if path == "/api/replay/run":
            return HttpRouteResponse.json(self._control.replay_run(ControlPlaneService.post_data(http)))

        if path == "/api/reflect/meta":
            return HttpRouteResponse.json(self._control.reflect_meta(ControlPlaneService.post_data(http)))

        if path == "/api/conflict/resolve":
            payload, status = self._control.conflict_resolve(ControlPlaneService.post_data(http))
            return HttpRouteResponse.json(payload, status)

        if path == "/api/conflict/settings":
            payload, status = self._control.conflict_settings(ControlPlaneService.post_data(http))
            return HttpRouteResponse.json(payload, status)

        if path == "/api/pruning/run":
            payload, status = self._control.pruning_run(ControlPlaneService.post_data(http))
            return HttpRouteResponse.json(payload, status)

        if path == "/api/consensus/reputation":
            payload, status = self._control.consensus_reputation(ControlPlaneService.post_data(http))
            return HttpRouteResponse.json(payload, status)

        if path == "/v1/cse/synthesize":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.cse_synthesize(data))

        if path == "/v1/ollama/start":
            return HttpRouteResponse.json(self._control.ollama_start())

        if path == "/v1/ollama/stop":
            return HttpRouteResponse.json(self._control.ollama_stop())

        if path == "/v1/gateway/intent":
            return HttpRouteResponse.json(self._gateway_intent.handle(ControlPlaneService.post_data(http)))

        if path.startswith("/v1/"):
            return HttpRouteResponse.json(self._snapshot.build())

        return None
