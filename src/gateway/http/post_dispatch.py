"""POST request dispatch across route callables returning HttpRouteResponse.

Route order in app_v2 V2Bindings.post_routes (first match wins):
  1. converse  — /api/converse, streaming chat
  2. asset     — uploads, asset CRUD
  3. peer      — P2P sync, handshake, DHT
  4. ingest    — document/code/image ingest
  5. control   — memory clear, replay, conflict, /v1/gateway/intent, /v1/* fallback
  6. models    — model registry HTTP API

Each entry is a PostRouteFn: (handler, path, query) -> HttpRouteResponse | None
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from .responses import HttpRouteResponse, apply_route_response

PostRouteFn = Callable[[Any, str, Optional[str]], Optional[HttpRouteResponse]]


def dispatch_post(
    handler: Any,
    path: str,
    query: Optional[str],
    routes: Iterable[PostRouteFn],
) -> bool:
    """Try each route fn; return True when a handler responds."""
    for route_fn in routes:
        response = route_fn(handler, path, query)
        if response is not None:
            apply_route_response(handler, response)
            return True
    return False
