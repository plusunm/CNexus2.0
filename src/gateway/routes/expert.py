"""Expert distillation API — distill / fact-confirm / subjects."""

from __future__ import annotations

from typing import Any, Optional

from ..http.responses import HttpRouteResponse
from ..services.expert_gateway import ExpertGatewayService


class ExpertRouteHandler:
    def __init__(self, service: ExpertGatewayService):
        self._service = service

    def handle_get(self, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        if path == "/api/expert/subjects":
            return HttpRouteResponse.json(self._service.list_subjects())
        return None

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        data = http._get_post_data() if hasattr(http, "_get_post_data") else {}
        if path == "/api/expert/distill":
            result = self._service.distill(data)
            return HttpRouteResponse.json(result, 400 if not result.get("ok") else 200)
        if path == "/api/expert/fact-confirm":
            result = self._service.fact_confirm(data)
            return HttpRouteResponse.json(result, 400 if not result.get("ok") else 200)
        if path == "/api/expert/capture":
            result = self._service.capture(data)
            return HttpRouteResponse.json(result, 400 if not result.get("ok") else 200)
        return None
