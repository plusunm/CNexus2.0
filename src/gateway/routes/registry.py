"""V2 route registry — post/put dispatch lists."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from ..http.post_dispatch import PostRouteFn
from ..http.responses import HttpRouteResponse
from .asset import AssetRouteHandler
from .converse import ConverseRouteHandler
from .control import ControlRouteHandler
from .ingest import IngestRouteHandler
from .models import ModelsRouteHandler
from .peer import PeerRouteHandler


def build_post_routes(
    converse: ConverseRouteHandler,
    asset: AssetRouteHandler,
    peer: PeerRouteHandler,
    ingest: IngestRouteHandler,
    control: ControlRouteHandler,
    models: ModelsRouteHandler,
) -> Tuple[PostRouteFn, ...]:
    """Ordered POST handlers — first match wins (see post_dispatch.py)."""

    def _converse(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return converse.handle_post(path, handler)

    def _asset(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return asset.handle_post(path, handler)

    def _peer(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return peer.handle_post(path, handler)

    def _ingest(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return ingest.handle_post(path, handler)

    def _control(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return control.handle_post(path, handler)

    def _models(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return models.handle_http_post(path, handler._read_json(), query)

    return (_converse, _asset, _peer, _ingest, _control, _models)


def build_put_routes(models: ModelsRouteHandler) -> Sequence[Any]:
    return (models,)
