"""GET/POST /api/analyze* — relationship decision analysis API."""

from __future__ import annotations

from typing import Any, Optional

from ..http.responses import HttpRouteResponse
from ..services.control_plane import ControlPlaneService
from ..services.relationship_analyze import RelationshipAnalyzeService


class AnalyzeRouteHandler:
    def __init__(self, service: RelationshipAnalyzeService):
        self._service = service

    def handle_get(self, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        if path == "/api/analyze/cards":
            return HttpRouteResponse.json(self._service.list_cards())

        if path.startswith("/api/analyze/cards/"):
            card_id = path[len("/api/analyze/cards/") :].strip("/")
            if not card_id:
                return None
            payload = self._service.get_card(card_id)
            status = 404 if payload.get("ok") is False else 200
            return HttpRouteResponse.json(payload, status)

        return None

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path == "/api/analyze":
            data = ControlPlaneService.post_data(http)
            payload = self._service.analyze(data)
            status = 400 if payload.get("ok") is False and payload.get("error") == "missing text" else (
                500 if payload.get("ok") is False else 200
            )
            return HttpRouteResponse.json(payload, status)

        if path == "/api/analyze/cards/delete":
            data = ControlPlaneService.post_data(http)
            return HttpRouteResponse.json(self._service.delete_card(data))

        if path == "/api/analyze/timeline":
            data = ControlPlaneService.post_data(http)
            payload = self._service.analyze_timeline(data)
            status = 400 if payload.get("ok") is False else 200
            return HttpRouteResponse.json(payload, status)

        return None
