"""HTTP/SSE adapters for converse service."""

from __future__ import annotations

from typing import Any, Iterator, Optional

from urllib.parse import parse_qs

from ..http.responses import HttpRouteResponse
from ..services.converse import ConverseService
from ..services.converse_config import ConverseConfigService
from ..services.converse_events import event_to_sse_string


class ConverseRouteHandler:
    def __init__(
        self,
        service: ConverseService,
        config: ConverseConfigService,
        *,
        stream_default: bool = False,
    ):
        self._service = service
        self._config = config
        self._stream_default = stream_default

    def handle_get(self, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        """GET /api/converse?text=... — blocking 6-step cycle."""
        if path != "/api/converse":
            return None
        qs = parse_qs(query or "")
        text = (qs.get("text") or [None])[0]
        if not text:
            return None
        data = {k: v[0] for k, v in qs.items() if v}
        converse_mode, thinking_mode = self._config.parse_request_modes(data)
        memory_scope = self._config.parse_memory_scope(data)
        model_id = data.get("model_id")
        try:
            result = self._service.run_blocking(
                str(text),
                model_id=model_id,
                converse_mode=converse_mode,
                thinking_mode=thinking_mode,
                memory_scope=memory_scope,
            )
            return HttpRouteResponse.json(
                {"ok": True, "status": "success", "reply": result["reply"], **result}
            )
        except Exception as exc:
            return HttpRouteResponse.json({"ok": False, "error": str(exc)}, 500)

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path == "/api/converse/stream":
            return self._handle_stream_post(http)
        if path == "/api/converse":
            return self._handle_converse_post(http)
        return None

    def _handle_stream_post(self, http: Any) -> HttpRouteResponse:
        try:
            data = http._get_post_data()
            text = data.get("text") or data.get("message", "")
            if not text:
                return HttpRouteResponse.json({"ok": False, "error": "missing text"}, 400)
            converse_mode, thinking_mode = self._config.parse_request_modes(data)
            memory_scope = self._config.parse_memory_scope(data)
            return HttpRouteResponse.sse(
                self.iter_sse_strings(
                    str(text),
                    model_id=data.get("model_id"),
                    converse_mode=converse_mode,
                    thinking_mode=thinking_mode,
                    memory_scope=memory_scope,
                )
            )
        except Exception as exc:
            return HttpRouteResponse.json({"ok": False, "error": str(exc)}, 500)

    def _handle_converse_post(self, http: Any) -> HttpRouteResponse:
        try:
            data = http._get_post_data()
            text = data.get("text") or data.get("message", "")
            if not text:
                return HttpRouteResponse.json({"ok": False, "error": "missing text"}, 400)
            model_id = data.get("model_id")
            converse_mode, thinking_mode = self._config.parse_request_modes(data)
            memory_scope = self._config.parse_memory_scope(data)
            accept_header_stream = "text/event-stream" in (http.headers.get("Accept") or "").lower()
            want_stream = self._stream_default and (
                data.get("stream") is True
                or str(data.get("stream", "")).lower() in ("1", "true", "yes")
                or accept_header_stream
            )
            if want_stream:
                return HttpRouteResponse.sse(
                    self.iter_sse_strings(
                        str(text),
                        model_id=model_id,
                        converse_mode=converse_mode,
                        thinking_mode=thinking_mode,
                        memory_scope=memory_scope,
                    )
                )
            result = self._service.run_blocking(
                str(text),
                model_id=model_id,
                converse_mode=converse_mode,
                thinking_mode=thinking_mode,
                memory_scope=memory_scope,
            )
            return HttpRouteResponse.json(
                {"ok": True, "status": "success", "reply": result["reply"], **result}
            )
        except Exception as exc:
            return HttpRouteResponse.json({"ok": False, "error": str(exc)}, 500)

    def iter_sse_strings(
        self,
        input_text: str,
        *,
        model_id: Optional[str] = None,
        converse_mode: str = "fast",
        thinking_mode: str = "precision",
        memory_scope: str = "local",
        session_id: Optional[str] = None,
    ) -> Iterator[str]:
        for event in self._service.stream_message(
            input_text,
            session_id=session_id,
            model_id=model_id,
            converse_mode=converse_mode,
            thinking_mode=thinking_mode,
            memory_scope=memory_scope,
        ):
            yield event_to_sse_string(event)
