"""V2 HTTP handler factory — thin dispatch shell over domain route handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
from urllib.parse import urlparse

from ..http.post_dispatch import PostRouteFn, dispatch_post
from ..http.put_dispatch import dispatch_put
from ..http.responder import HttpResponderMixin
from ..http.responses import apply_route_response


@dataclass
class V2Bindings:
    models_routes: Any
    converse_routes: Any
    ingest_routes: Any
    status_routes: Any
    asset_routes: Any
    peer_routes: Any
    control_routes: Any
    static_routes: Any
    auth_gate: Any
    put_routes: Sequence[Any]
    post_routes: Sequence[PostRouteFn]
    expert_routes: Any = None


def create_v2_handler(bindings: V2Bindings):
    class V2Handler(HttpResponderMixin):
        def log_message(self, format, *args):
            return

        def do_PUT(self):
            p = urlparse(self.path)
            path = p.path.rstrip("/") or "/"
            if not dispatch_put(self, path, bindings.put_routes):
                self._json({"ok": False, "error": "not found"}, 404)

        def do_GET(self):
            p = urlparse(self.path)
            path = p.path.rstrip("/") or "/"

            if self.headers.get("Upgrade", "").lower() == "websocket":
                return self._reject_websocket_upgrade()

            status_get = bindings.status_routes.handle_get(path, p.query)
            if status_get is not None:
                return apply_route_response(self, status_get)

            asset_get = bindings.asset_routes.handle_get(path, p.query, self.headers)
            if asset_get is not None:
                return apply_route_response(self, asset_get)

            peer_get = bindings.peer_routes.handle_get(path, p.query, self.headers)
            if peer_get is not None:
                return apply_route_response(self, peer_get)

            converse_get = bindings.converse_routes.handle_get(path, p.query)
            if converse_get is not None:
                return apply_route_response(self, converse_get)

            if bindings.expert_routes is not None:
                expert_get = bindings.expert_routes.handle_get(path, p.query)
                if expert_get is not None:
                    return apply_route_response(self, expert_get)

            models_get = bindings.models_routes.handle_http_get(path, p.query)
            if models_get is not None:
                return apply_route_response(self, models_get)

            return apply_route_response(self, bindings.static_routes.handle_get(path))

        def do_POST(self):
            p = urlparse(self.path)
            path = p.path.rstrip("/") or "/"
            if not bindings.auth_gate.allow(self, path):
                return

            if dispatch_post(self, path, p.query, bindings.post_routes):
                return

            self._json({"ok": False, "error": "not found"}, 404)

    return V2Handler
