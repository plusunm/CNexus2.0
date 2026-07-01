"""V2 route registry — post/put dispatch lists."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from ..http.post_dispatch import PostRouteFn
from ..http.responses import HttpRouteResponse
from .analyze import AnalyzeRouteHandler
from .asset import AssetRouteHandler
from .converse import ConverseRouteHandler
from .control import ControlRouteHandler
from .expert import ExpertRouteHandler
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
    expert: Optional[ExpertRouteHandler] = None,
    analyze: Optional[AnalyzeRouteHandler] = None,
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

    def _expert(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        if expert is None:
            return None
        return expert.handle_post(path, handler)

    def _analyze(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        if analyze is None:
            return None
        return analyze.handle_post(path, handler)

    routes: Tuple[PostRouteFn, ...] = (_converse, _asset, _peer, _ingest, _control, _models)
    if analyze is not None:
        routes = routes + (_analyze,)
    if expert is not None:
        routes = routes + (_expert,)
    return routes


def build_get_expert_route(expert: Optional[ExpertRouteHandler]):
    if expert is None:
        return None

    def _expert_get(handler: Any, path: str, query: Optional[str]) -> Optional[HttpRouteResponse]:
        return expert.handle_get(path, query)

    return _expert_get


def build_put_routes(models: ModelsRouteHandler) -> Sequence[Any]:
    return (models,)
