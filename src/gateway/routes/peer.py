"""Peer sync, audit, DHT, and connectivity routes."""

from __future__ import annotations

import json
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

        if path == "/api/connectivity/identity":
            payload, status = self._mesh.connectivity_identity()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/connectivity/bootstrap-peers":
            payload, status = self._mesh.connectivity_bootstrap_peers()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/connectivity/resolve":
            pubkey = qs.get("pubkey", [""])[0] or qs.get("peer_id", [""])[0] or ""
            payload, status = self._mesh.connectivity_resolve(pubkey)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/connectivity/directory":
            limit_raw = qs.get("limit", ["128"])[0] or "128"
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 128
            payload, status = self._mesh.connectivity_directory(limit=limit)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/generation":
            payload, status = self._mesh.catalog_generation_get()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/bloom/summary":
            namespace = qs.get("namespace", ["catalog/system"])[0] or "catalog/system"
            payload, status = self._mesh.catalog_bloom_summary_get(namespace=namespace)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/head":
            graph_id = qs.get("graph_id", [""])[0] or ""
            payload, status = self._mesh.catalog_head_get(graph_id)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/bloom":
            namespace = qs.get("namespace", ["catalog/system"])[0] or "catalog/system"
            payload, status = self._mesh.catalog_bloom_get(namespace=namespace)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/index":
            limit_raw = qs.get("limit", ["256"])[0] or "256"
            namespace = qs.get("namespace", ["catalog/system"])[0] or "catalog/system"
            cursors_raw = qs.get("commit_cursors", ["{}"])[0] or "{}"
            interest_raw = qs.get("interest", ["{}"])[0] or "{}"
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 256
            try:
                commit_cursors = json.loads(cursors_raw)
            except json.JSONDecodeError:
                commit_cursors = {}
            graph_id = qs.get("graph_id", [""])[0] or ""
            since_commit_id = qs.get("since_commit_id", [""])[0] or ""
            if graph_id and since_commit_id:
                commit_cursors[str(graph_id)] = since_commit_id
            try:
                interest = json.loads(interest_raw)
            except json.JSONDecodeError:
                interest = {}
            payload, status = self._mesh.catalog_index_get(
                commit_cursors=commit_cursors if isinstance(commit_cursors, dict) else {},
                namespace=namespace,
                limit=limit,
                interest=interest if isinstance(interest, dict) else {},
            )
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/status":
            payload, status = self._mesh.catalog_status()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/cognitive/head":
            graph_id = qs.get("graph_id", [""])[0] or ""
            payload, status = self._mesh.cognitive_head_get(graph_id)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/cognitive/dag":
            graph_id = qs.get("graph_id", [""])[0] or ""
            limit_raw = qs.get("limit", ["512"])[0] or "512"
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 512
            payload, status = self._mesh.cognitive_dag_get(graph_id, limit=limit)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/cognitive/commits":
            graph_id = qs.get("graph_id", [""])[0] or ""
            since_commit_id = qs.get("since_commit_id", [""])[0] or ""
            limit_raw = qs.get("limit", ["256"])[0] or "256"
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 256
            payload, status = self._mesh.cognitive_commits_get(
                graph_id,
                since_commit_id=since_commit_id,
                limit=limit,
            )
            return HttpRouteResponse.json(payload, status)

        if path == "/api/cognitive/status":
            payload, status = self._mesh.cognitive_status()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/application/status":
            payload, status = self._mesh.application_status()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/manifest":
            root_hash = qs.get("root_hash", [""])[0] or ""
            commit_id = qs.get("commit_id", [""])[0] or ""
            payload, status = self._mesh.storage_manifest_get(root_hash=root_hash, commit_id=commit_id)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/chunk/state":
            chunk_hash = qs.get("hash", [""])[0] or qs.get("chunk_hash", [""])[0] or ""
            payload, status = self._mesh.storage_chunk_state(chunk_hash)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/chunk":
            chunk_hash = qs.get("hash", [""])[0] or qs.get("chunk_hash", [""])[0] or ""
            if chunk_hash:
                payload, status = self._mesh.storage_chunk_get(chunk_hash)
                return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/chunk/has":
            chunk_hash = qs.get("hash", [""])[0] or qs.get("chunk_hash", [""])[0] or ""
            payload, status = self._mesh.storage_chunk_has(chunk_hash)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/chunk/verify":
            chunk_hash = qs.get("hash", [""])[0] or qs.get("chunk_hash", [""])[0] or ""
            payload, status = self._mesh.storage_chunk_verify(chunk_hash)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/status":
            payload, status = self._mesh.storage_status()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/diff":
            root_hash = qs.get("root_hash", [""])[0] or ""
            commit_id = qs.get("commit_id", [""])[0] or ""
            scope = qs.get("scope", ["manifest"])[0] or "manifest"
            payload, status = self._mesh.repair_diff_get(
                root_hash=root_hash,
                commit_id=commit_id,
                scope=scope,
            )
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/policy":
            payload, status = self._mesh.repair_policy_get()
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
            hint_host = str(
                data.get("host")
                or data.get("peer_host")
                or data.get("url")
                or ""
            ).strip()
            payload, status = self._mesh.connectivity_connect(peer_id, hint_host=hint_host)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/connectivity/register":
            payload, status = self._mesh.connectivity_register(http._get_post_data(), http.headers)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/bloom":
            data = http._get_post_data()
            payload, status = self._mesh.catalog_bloom_exchange(data)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/index":
            data = http._get_post_data()
            payload, status = self._mesh.catalog_index_exchange(data)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/catalog/register":
            payload, status = self._mesh.catalog_register(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/cognitive/commits":
            payload, status = self._mesh.cognitive_commits_post(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/cognitive/publish":
            payload, status = self._mesh.cognitive_publish(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/chunk":
            payload, status = self._mesh.storage_chunk_put(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/chunk/pull":
            payload, status = self._mesh.storage_chunk_pull(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/manifest/verify":
            payload, status = self._mesh.storage_manifest_verify(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/plan":
            payload, status = self._mesh.repair_plan_post(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/execute":
            payload, status = self._mesh.repair_execute_post(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/hook":
            payload, status = self._mesh.repair_hook_post(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/policy":
            payload, status = self._mesh.repair_policy_post(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/storage/repair/gate":
            payload, status = self._mesh.repair_gate_post(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/application/publish":
            payload, status = self._mesh.application_publish(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/application/find":
            payload, status = self._mesh.application_find(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/application/sync":
            payload, status = self._mesh.application_sync(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/application/diagnose":
            payload, status = self._mesh.application_diagnose(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/application/repair":
            payload, status = self._mesh.application_repair(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        if path == "/api/network/firewall/ban":
            payload, status = self._mesh.network_firewall_ban(http._get_post_data())
            return HttpRouteResponse.json(payload, status)

        return None
