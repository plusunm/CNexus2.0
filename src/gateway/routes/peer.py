"""Peer sync, audit, DHT, and connectivity routes."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import parse_qs

from ..http.auth_gate import AuthGate
from ..http.responses import HttpRouteResponse
from ..services.peer_mesh import PeerMeshService


class PeerRouteHandler:
    """P2P / peer mesh APIs — returns None when path is not handled."""

    def __init__(self, mesh: PeerMeshService, auth: AuthGate):
        self._mesh = mesh
        self._auth = auth

    def handle_get(self, path: str, query: Optional[str], headers: Any) -> Optional[HttpRouteResponse]:
        qs = parse_qs(query or "")

        if path == "/api/peer/audit":
            since_hash = qs.get("since_hash", ["0"])[0] or "0"
            try:
                limit = int(qs.get("limit", ["0"])[0] or "0")
            except ValueError:
                limit = 0
            denied = self._auth.check(
                path,
                headers,
                {"since_hash": since_hash, "limit": limit},
                method="GET",
            )
            if denied is not None:
                err, status = denied
                return HttpRouteResponse.json(err, status)
            payload, status = self._mesh.peer_audit(since_hash, headers, limit=limit)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/peer/audit-proof":
            denied = self._auth.check(path, headers, {"action": "proof"}, method="GET")
            if denied is not None:
                err, status = denied
                return HttpRouteResponse.json(err, status)
            payload, status = self._mesh.peer_audit_proof(headers)
            return HttpRouteResponse.json(payload, status)

        return None

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path == "/api/peer/force-sync":
            payload, status = self._mesh.peer_force_sync(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/peer/sync":
            payload, status = self._mesh.peer_sync(http._get_post_data(), http.headers)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/peer/negotiate":
            payload, status = self._mesh.peer_negotiate(http._get_post_data(), http.headers)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/p2p/handshake":
            payload, status = self._mesh.p2p_handshake(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/dht/rpc":
            payload, status = self._mesh.dht_rpc(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/connectivity/connect":
            data = http._get_post_data()
            peer_id = str(data.get("peer_id") or data.get("pubkey") or "")
            payload, status = self._mesh.connectivity_connect(peer_id)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/network/firewall/ban":
            payload, status = self._mesh.network_firewall_ban(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        return None
