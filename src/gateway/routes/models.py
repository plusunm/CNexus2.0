"""HTTP route handlers for model registry endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs

from ..http.responses import HttpRouteResponse
from ..services.models import ModelConfigService

JsonResponse = Tuple[Dict[str, Any], int]


def is_models_path(path: str) -> bool:
    return path in ("/models", "/api/models") or path.startswith("/models/") or path.startswith("/api/models/")


def is_models_mutation_path(path: str) -> bool:
    return path.startswith("/models/") or path.startswith("/api/models/")


def normalize_models_path(path: str) -> str:
    """Map /api/models/* to /models/* for unified dispatch."""
    if path == "/api/models":
        return "/models"
    if path.startswith("/api/models/"):
        return "/models/" + path[len("/api/models/") :]
    return path


def parse_quick_flag(query: Optional[str]) -> bool:
    qs = parse_qs(query or "")
    return (qs.get("quick", ["false"])[0] or "").lower() in ("1", "true", "yes")


class ModelsRouteHandler:
    """Thin adapter between stdlib HTTP handler and ModelConfigService."""

    def __init__(self, service: ModelConfigService):
        self._service = service

    def handle_get(self, path: str, query: Optional[str] = None) -> JsonResponse:
        path = normalize_models_path(path.rstrip("/") or "/")
        if path == "/models":
            return self._service.list_models(), 200
        if path.startswith("/models/") and path.endswith("/test"):
            model_id = path[len("/models/") : -len("/test")]
            return self._service.test(model_id, quick=parse_quick_flag(query)), 200
        if path.startswith("/models/"):
            model_id = path[len("/models/") :]
            row = self._service.get_model(model_id)
            if not row:
                return {"detail": f"model not found: {model_id}"}, 404
            return {"model": row}, 200
        return {"ok": False, "error": "not found"}, 404

    def handle_put(self, path: str, body: Dict[str, Any]) -> JsonResponse:
        path = normalize_models_path(path.rstrip("/") or "/")
        if not path.startswith("/models/"):
            return {"ok": False, "error": "not found"}, 404
        model_id = path[len("/models/") :]
        row, err = self._service.upsert(model_id, body, create=False)
        if err == "not_found":
            return {"detail": f"model not found: {model_id}"}, 404
        return {"model": row}, 200

    def handle_post(self, path: str, body: Dict[str, Any], query: Optional[str] = None) -> JsonResponse:
        path = normalize_models_path(path.rstrip("/") or "/")
        if path == "/models":
            row, err = self._service.create(body)
            if err:
                return {"detail": err}, 400
            return {"model": row}, 200
        if path.startswith("/models/") and path.endswith("/test"):
            model_id = path[len("/models/") : -len("/test")]
            return self._service.test(model_id, quick=parse_quick_flag(query)), 200
        return {"ok": False, "error": "not found"}, 404

    def handle_http_get(self, path: str, query: Optional[str] = None) -> Optional[HttpRouteResponse]:
        if not is_models_path(path):
            return None
        payload, status = self.handle_get(path, query)
        return HttpRouteResponse.json(payload, status)

    def handle_http_post(
        self,
        path: str,
        body: Dict[str, Any],
        query: Optional[str] = None,
    ) -> Optional[HttpRouteResponse]:
        if not is_models_path(path):
            return None
        payload, status = self.handle_post(path, body, query)
        return HttpRouteResponse.json(payload, status)

    def handle_http_put(self, path: str, body: Dict[str, Any]) -> Optional[HttpRouteResponse]:
        if not is_models_mutation_path(path):
            return None
        payload, status = self.handle_put(path, body)
        return HttpRouteResponse.json(payload, status)

    def handle_put_route(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        return self.handle_http_put(path, http._read_json())
