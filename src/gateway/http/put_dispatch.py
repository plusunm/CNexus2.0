"""PUT request dispatch across route handlers with handle_put_route."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from .responses import HttpRouteResponse, apply_route_response


def dispatch_put(handler: Any, path: str, routes: Iterable[Any]) -> bool:
    """Try each route's handle_put_route; return True when a handler responds."""
    for route in routes:
        put = getattr(route, "handle_put_route", None)
        if put is None:
            continue
        response: Optional[HttpRouteResponse] = put(path, handler)
        if response is not None:
            apply_route_response(handler, response)
            return True
    return False
