"""Asset + peer route bootstrap — memory asset, gateway, mesh, route handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..http.auth_gate import AuthGate
from ..routes.asset import AssetRouteHandler
from ..routes.ingest import IngestRouteHandler
from ..routes.peer import PeerRouteHandler
from ..state import EngineStateManager
from .asset_gateway import AssetGatewayHooks, AssetGatewayService
from .memory.asset import MemoryAssetHooks, MemoryAssetService
from .memory.query import MemoryQueryService
from .peer_mesh import PeerMeshHooks, PeerMeshService
from .projection_ingest import ProjectionIngestService


@dataclass(frozen=True)
class AssetRouteBootstrapHooks:
    """App-wired hooks for asset stack + peer mesh."""

    memory_asset: MemoryAssetHooks
    asset_gateway: AssetGatewayHooks
    peer_mesh: PeerMeshHooks


@dataclass
class AssetRouteBootstrapServices:
    """Constructed asset/peer services and HTTP route handlers."""

    memory_asset: MemoryAssetService
    asset_gateway: AssetGatewayService
    peer_mesh: PeerMeshService
    asset_routes: AssetRouteHandler
    peer_routes: PeerRouteHandler


def build_asset_route_services(
    state: EngineStateManager,
    memory_recall: MemoryQueryService,
    auth: AuthGate,
    ingest_routes: IngestRouteHandler,
    projection_ingest: ProjectionIngestService,
    hooks: AssetRouteBootstrapHooks,
    *,
    touch_activity: Callable[[], None],
) -> AssetRouteBootstrapServices:
    """Wire memory asset port, asset gateway, peer mesh, and route handlers."""
    memory_asset = MemoryAssetService(state, memory_recall, hooks.memory_asset)
    memory_recall.attach_assets(memory_asset)

    asset_gateway = AssetGatewayService(
        hooks.asset_gateway,
        auth,
        projection_ingest,
        memory_assets=memory_asset,
        touch_activity=touch_activity,
    )
    peer_mesh = PeerMeshService(hooks.peer_mesh)

    return AssetRouteBootstrapServices(
        memory_asset=memory_asset,
        asset_gateway=asset_gateway,
        peer_mesh=peer_mesh,
        asset_routes=AssetRouteHandler(asset_gateway, ingest_routes, auth),
        peer_routes=PeerRouteHandler(peer_mesh, auth),
    )
