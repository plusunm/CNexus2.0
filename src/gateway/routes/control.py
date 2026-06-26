"""Control-plane POST routes — memory, replay, conflict, pruning, ollama."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..http.responses import HttpRouteResponse
from ..services.control_plane import ControlPlaneService
from ..services.gateway_intent import GatewayIntentService
from ..services.project_control import ProjectControlService
from ..services.status_snapshot import StatusSnapshotService


class ControlRouteHandler:
    """Cognitive control APIs — returns None when path is not handled."""

    def __init__(
        self,
        control: ControlPlaneService,
        snapshot: StatusSnapshotService,
        gateway_intent: GatewayIntentService,
        project_control: ProjectControlService | None = None,
        clear_scratch: Callable[[], Dict[str, Any]] | None = None,
    ):
        self._control = control
        self._snapshot = snapshot
        self._gateway_intent = gateway_intent
        self._project_control = project_control
        self._clear_scratch = clear_scratch

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path in ("/api/memory/clear", "/v1/memory/clear"):
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.memory_clear(data))

        if path == "/v1/memory/rem-sleep":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.rem_sleep(data))

        if path == "/v1/memory/promote":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.memory_promote(data))

        if path == "/v1/memory/foundation/upgrade":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.memory_foundation_upgrade(data))

        if path == "/v1/memory/constitution/bootstrap":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.memory_constitution_bootstrap(data))

        if path == "/v1/runtime/recompile":
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._control.runtime_recompile(data))

        if path == "/v1/project/active" and self._project_control is not None:
            data = ControlPlaneService.read_json_body(http)
            return HttpRouteResponse.json(self._project_control.set_active(data))

        if path == "/v1/project/unlock" and self._project_control is not None:
            return HttpRouteResponse.json(self._project_control.unlock())

        if path == "/v1/conversation/scratch/clear" and self._clear_scratch is not None:
            return HttpRouteResponse.json(self._clear_scratch())

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
