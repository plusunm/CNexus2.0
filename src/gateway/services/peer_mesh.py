"""Peer mesh sync, audit, DHT, and connectivity operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from ..http.auth_gate import AuthGate

JsonResponse = Tuple[Any, int]
AuthDenyFn = Callable[..., Optional[JsonResponse]]


@dataclass(frozen=True)
class PeerMeshHooks:
    get_audit_log: Callable[[], Any]
    get_peer_registry: Callable[[], Any]
    get_gossip_sync: Callable[[], Any]
    get_genesis_sync: Callable[[], Any]
    get_p2p_handler: Callable[[], Any]
    get_negotiation_manager: Callable[[], Any]
    get_entropy_store: Callable[[], Any]
    get_connectivity_manager: Callable[[], Any]
    get_dht_service: Callable[[], Any]
    get_network_firewall: Callable[[], Any]
    header_lookup_peer: Callable[[Any], str]
    verify_audit_integrity: Callable[[], Dict[str, Any]]
    identity_pubkey: Callable[[], str]
    audit_event: Callable[..., None]
    perform_outbound_handshake: Callable[..., Dict[str, Any]]
    local_peer_host: Callable[[], str]
    get_catalog_service: Callable[[], Any]
    get_cognitive_service: Callable[[], Any]
    get_storage_service: Callable[[], Any]
    get_repair_service: Callable[[], Any]
    get_application_service: Callable[[], Any]
    memory_block_count: Callable[[], int]
    trace_count: Callable[[], int]


class PeerMeshService:
    """P2P / peer mesh APIs — no HTTP objects."""

    def __init__(self, hooks: PeerMeshHooks):
        self._hooks = hooks

    def peer_audit(self, since_hash: str, headers: Any, *, limit: int = 0) -> JsonResponse:
        audit = self._hooks.get_audit_log()
        if audit is None:
            return {"ok": False, "error": "audit_unavailable"}, 503
        since_hash = str(since_hash or "0")
        if limit > 0:
            entries, anchor_found, has_more = audit.get_entries_chunk(since_hash, limit=limit)
        else:
            entries, anchor_found = audit.get_entries_since(since_hash)
            has_more = False
        peer = self._hooks.header_lookup_peer(headers)
        reg = self._hooks.get_peer_registry()
        if reg and peer:
            reg.touch_peer(str(peer))
        return {
            "ok": True,
            "since_hash": since_hash,
            "anchor_found": anchor_found,
            "entries": entries,
            "entry_count": len(entries),
            "has_more": has_more,
            "last_hash": audit.last_hash,
            "node_pubkey": self._hooks.identity_pubkey(),
        }, 200

    def peer_audit_proof(self, headers: Any) -> JsonResponse:
        audit = self._hooks.get_audit_log()
        if audit is None:
            return {"ok": False, "error": "audit_unavailable"}, 503
        peer = self._hooks.header_lookup_peer(headers)
        reg = self._hooks.get_peer_registry()
        if reg and peer:
            reg.touch_peer(str(peer))
        hashes = audit.get_proof_hashes()
        return {
            "ok": True,
            "hashes": hashes[-128:],
            "entry_count": audit.entry_count(),
            "last_hash": audit.last_hash,
            "node_pubkey": self._hooks.identity_pubkey(),
        }, 200

    def peer_force_sync(self, data: Dict[str, Any]) -> JsonResponse:
        gossip = self._hooks.get_gossip_sync()
        if gossip is None:
            return {"ok": False, "error": "gossip_unavailable"}, 503
        payload = data or {}
        pubkey = str(payload.get("pubkey") or payload.get("peer_pubkey") or "").strip()
        host = str(payload.get("host") or payload.get("peer_host") or "").strip()
        reg = self._hooks.get_peer_registry()
        if reg and pubkey and not host:
            host = str((reg.get_all_peers().get(pubkey) or {}).get("host") or "")
        if not host:
            return {"ok": False, "error": "missing_peer_host"}, 400
        genesis = bool(payload.get("genesis"))
        if genesis:
            genesis_sync = self._hooks.get_genesis_sync()
            if genesis_sync is None:
                return {"ok": False, "error": "genesis_unavailable"}, 503
            result = genesis_sync.genesis_handshake(host, peer_pubkey=pubkey)
        else:
            result = gossip.check_sync(host, peer_pubkey=pubkey)
        self._hooks.audit_event(
            "peer.force_sync",
            {
                "peer_pubkey": pubkey[:64],
                "host": host,
                "genesis": genesis,
                "ok": bool(result.get("ok")),
                "error": result.get("error"),
            },
        )
        code = 200 if result.get("ok") else 502
        return {"ok": bool(result.get("ok")), "result": result, "genesis": genesis}, code

    def peer_sync(self, data: Dict[str, Any], headers: Any) -> JsonResponse:
        audit = self._hooks.get_audit_log()
        local_hash = audit.last_hash if audit else "0"
        remote_hash = str((data or {}).get("last_hash") or "")
        action = str((data or {}).get("action") or "gossip_check").upper()
        peer = (data or {}).get("pubkey") or self._hooks.header_lookup_peer(headers)
        reg = self._hooks.get_peer_registry()
        if reg and peer:
            reg.touch_peer(str(peer))
        store = self._hooks.get_entropy_store()
        recorded_entropy = None
        if store and peer and (data or {}).get("entropy_seed"):
            recorded_entropy = store.record_peer_seed(reg, str(peer), data.get("entropy_seed"))
        integrity = self._hooks.verify_audit_integrity()
        self._hooks.audit_event(
            "peer.sync",
            {
                "peer_pubkey": str(peer)[:64],
                "remote_hash": remote_hash[:16],
                "aligned": remote_hash == local_hash,
                "action": action,
                "entropy_seed": str(recorded_entropy or "")[:18],
            },
        )
        payload = {
            "ok": True,
            "status": "genesis_ready" if action == "GENESIS_HANDSHAKE" else "synced",
            "action": action,
            "node_pubkey": self._hooks.identity_pubkey(),
            "last_hash": local_hash,
            "audit_entries": audit.entry_count() if audit else 0,
            "aligned": remote_hash == local_hash if remote_hash else None,
            "integrity_ok": integrity.get("ok", True),
            "memory_count": self._hooks.memory_block_count(),
            "trace_count": self._hooks.trace_count(),
            "protocol_version": "2.0",
        }
        if store:
            payload.update(store.genesis_payload_fields())
            payload["global_entropy"] = store.global_entropy_hex(reg)
        return payload, 200

    def peer_negotiate(self, data: Dict[str, Any], headers: Any) -> JsonResponse:
        neg = self._hooks.get_negotiation_manager()
        if neg is None:
            return {"ok": False, "error": "consensus_unavailable"}, 503
        peer = (data or {}).get("pubkey") or self._hooks.header_lookup_peer(headers)
        reg = self._hooks.get_peer_registry()
        if reg and peer:
            reg.touch_peer(str(peer))
        result = neg.handle_negotiate(data or {}, str(peer or ""))
        if not result.get("ok"):
            store = self._hooks.get_entropy_store()
            if store:
                result["global_entropy"] = store.global_entropy_hex(reg)
        self._hooks.audit_event(
            "peer.negotiate",
            {
                "action": (data or {}).get("action"),
                "peer_pubkey": str(peer)[:64],
                "vote": result.get("vote"),
                "status": result.get("status"),
                "ok": result.get("ok"),
            },
        )
        code = 200 if result.get("ok", True) else 400
        return result, code

    def p2p_handshake(self, data: Dict[str, Any]) -> JsonResponse:
        handler = self._hooks.get_p2p_handler()
        if handler is None:
            return {"ok": False, "error": "identity_unavailable"}, 503
        result = handler.handle_request(data or {})
        if not result.get("ok"):
            code = 403 if result.get("error") == "handshake_failed" else 400
            return result, code
        if result.get("status") == "trusted_peer":
            pubkey = str(result.get("pubkey") or "")
            host = str(data.get("host") or data.get("peer_host") or result.get("host") or "")
            reg = self._hooks.get_peer_registry()
            if reg and pubkey:
                reg.save_peer(pubkey, host, status="trusted")
            gossip = self._hooks.get_gossip_sync()
            if gossip and host:
                gossip.schedule_check(host, peer_pubkey=pubkey, genesis=True)
            self._hooks.audit_event("peer.handshake", {"peer_pubkey": pubkey[:64], "host": host})
        return result, 200

    def dht_rpc(self, payload: Dict[str, Any]) -> JsonResponse:
        dht = self._hooks.get_dht_service()
        if dht is None:
            return {"ok": False, "error": "dht_unavailable"}, 503
        return dht.handle_rpc(payload or {}), 200

    def connectivity_identity(self) -> JsonResponse:
        pubkey = str(self._hooks.identity_pubkey() or "").strip()
        if not pubkey:
            return {"ok": False, "error": "identity_unavailable"}, 503
        return {"ok": True, "pubkey": pubkey, "service": "cnexus-2.0-personal"}, 200

    def connectivity_connect(self, peer_id: str, *, hint_host: str = "") -> JsonResponse:
        cm = self._hooks.get_connectivity_manager()
        if cm is None:
            return {"ok": False, "error": "connectivity_unavailable"}, 503
        peer_id = str(peer_id or "").strip()
        if not peer_id:
            return {"ok": False, "error": "missing_peer_id"}, 400
        report = cm.connect_to(peer_id, hint_host=hint_host)
        if not report.get("ok"):
            code = 502 if report.get("error") else 400
            return report, code

        url = str(report.get("url") or "")
        handler = self._hooks.get_p2p_handler()
        reg = self._hooks.get_peer_registry()
        handshake_report: Dict[str, Any] = {"ok": False, "skipped": True, "reason": "identity_unavailable"}

        if handler and url:
            try:
                handshake_report = self._hooks.perform_outbound_handshake(
                    url,
                    peer_id,
                    handler,
                    self._hooks.local_peer_host(),
                )
                if handshake_report.get("ok") and reg:
                    reg.save_peer(peer_id, url, status="trusted")
                    handshake_report["local_trusts_remote"] = True
                    self._hooks.audit_event(
                        "peer.handshake",
                        {
                            "peer_pubkey": peer_id[:64],
                            "host": url,
                            "direction": "outbound",
                        },
                    )
            except Exception as exc:
                handshake_report = {"ok": False, "error": str(exc), "phase": "client"}

        report["handshake"] = handshake_report
        gossip = self._hooks.get_gossip_sync()
        if gossip and url and (handshake_report.get("ok") or handshake_report.get("skipped")):
            gossip.schedule_check(url, peer_pubkey=peer_id, genesis=False)

        catalog_report: Dict[str, Any] = {"ok": False, "skipped": True}
        catalog = self._hooks.get_catalog_service()
        if catalog and url and handshake_report.get("ok"):
            try:
                catalog_report = catalog.exchange_with_peer(url, peer_id=peer_id)
            except Exception as exc:
                catalog_report = {"ok": False, "error": str(exc), "phase": "catalog"}
        report["catalog"] = catalog_report

        cognitive_report: Dict[str, Any] = {"ok": False, "skipped": True}
        cognitive = self._hooks.get_cognitive_service()
        if cognitive and url and handshake_report.get("ok") and catalog_report.get("ok"):
            try:
                cognitive_report = cognitive.sync_from_catalog_peer(url, catalog_report)
            except Exception as exc:
                cognitive_report = {"ok": False, "error": str(exc), "phase": "cognitive"}
        report["cognitive"] = cognitive_report

        repair_hook: Dict[str, Any] = {"ok": False, "skipped": True}
        repair = self._hooks.get_repair_service()
        if repair and url and handshake_report.get("ok"):
            try:
                repair_hook = repair.build_connect_hook(
                    peer_host=url,
                    peer_id=peer_id,
                    peer_registry=reg,
                )
            except Exception as exc:
                repair_hook = {"ok": False, "error": str(exc), "phase": "repair_hook"}
        report["repair_hook"] = repair_hook

        application_view: Dict[str, Any] = {"ok": False, "skipped": True}
        application = self._hooks.get_application_service()
        if application is not None:
            try:
                application_view = application.absorb_connect(report)
            except Exception as exc:
                application_view = {"ok": False, "error": str(exc), "phase": "application"}
        report["application"] = application_view

        if handler and url and not handshake_report.get("ok") and not handshake_report.get("skipped"):
            report["ok"] = False
            report["error"] = str(handshake_report.get("error") or "handshake_failed")
            return report, 502

        return report, 200

    def catalog_generation_get(self) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        return catalog.generation_payload(), 200

    def catalog_head_get(self, graph_id: str) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        return catalog.get_head(graph_id)

    def catalog_bloom_summary_get(self, *, namespace: str = "catalog/system") -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        return catalog.get_bloom_summary(namespace), 200

    def catalog_bloom_get(self, *, namespace: str = "catalog/system") -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        return catalog.get_bloom_payload(namespace=namespace), 200

    def catalog_bloom_exchange(self, data: Dict[str, Any]) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        try:
            from catalog.interest import CatalogInterest
        except ImportError:
            from cnexus_catalog.interest import CatalogInterest
        remote_bloom = str((data or {}).get("bloom") or "")
        namespace = str((data or {}).get("namespace") or "catalog/system")
        remote_summary = (data or {}).get("summary") or {}
        interest = CatalogInterest.from_dict((data or {}).get("interest") or {})
        payload = catalog.exchange_bloom(
            remote_bloom,
            namespace=namespace,
            remote_summary=remote_summary,
        )
        payload["interest"] = interest.to_dict()
        return payload, 200

    def catalog_index_get(
        self,
        *,
        commit_cursors: Optional[Dict[str, str]] = None,
        namespace: str = "catalog/system",
        limit: int = 256,
        interest: Optional[Dict[str, Any]] = None,
    ) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        try:
            from catalog.interest import CatalogInterest
        except ImportError:
            from cnexus_catalog.interest import CatalogInterest
        return catalog.get_index_payload(
            since_commit_cursors=commit_cursors,
            interest=CatalogInterest.from_dict(interest or {}),
            namespace=namespace,
            limit=limit,
        ), 200

    def catalog_index_exchange(self, data: Dict[str, Any]) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        try:
            from catalog.interest import CatalogInterest
        except ImportError:
            from cnexus_catalog.interest import CatalogInterest
        limit = int((data or {}).get("limit") or 256)
        remote_entries = (data or {}).get("entries") or []
        if not isinstance(remote_entries, list):
            remote_entries = []
        cursors = (data or {}).get("commit_cursors") or (data or {}).get("since_commit_cursors") or {}
        namespace = str((data or {}).get("namespace") or "catalog/system")
        interest = CatalogInterest.from_dict((data or {}).get("interest") or {})
        return catalog.exchange_index(
            since_commit_cursors=cursors if isinstance(cursors, dict) else {},
            remote_entries=remote_entries,
            interest=interest,
            namespace=namespace,
            limit=limit,
        ), 200

    def catalog_register(self, data: Dict[str, Any]) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        try:
            from protocol.models import Commit, Graph
        except ImportError:
            from cnexus_protocol.models import Commit, Graph
        graph_row = (data or {}).get("graph") or {}
        commit_row = (data or {}).get("commit") or {}
        if not graph_row and (data or {}).get("graph_id"):
            graph_row = {"graph_id": data.get("graph_id"), "owner": data.get("owner") or self._hooks.identity_pubkey()}
        if not commit_row and (data or {}).get("latest_commit_id"):
            commit_row = {
                "graph_id": graph_row.get("graph_id") or data.get("graph_id"),
                "commit_id": data.get("latest_commit_id"),
                "root_hash": data.get("root_hash"),
                "author": graph_row.get("owner") or self._hooks.identity_pubkey(),
                "constitution_hash": (graph_row.get("metadata") or {}).get("constitution_hash") or ("00" * 32),
                "signature": data.get("signature") or "",
                "parent_ids": data.get("parent_ids") or [],
            }
        graph = Graph.from_dict(graph_row)
        commit = Commit.from_dict(commit_row)
        chunk_hashes = (data or {}).get("chunk_hashes") or []
        size = int((data or {}).get("size") or 0)
        entry = catalog.register_graph(graph, commit, chunk_hashes=chunk_hashes, size=size)
        self._hooks.audit_event(
            "catalog.register",
            {"graph_id": entry.graph_id, "commit_id": entry.latest_commit_id},
        )
        return {"ok": True, "entry": entry.to_dict()}, 200

    def catalog_status(self) -> JsonResponse:
        catalog = self._hooks.get_catalog_service()
        if catalog is None:
            return {"ok": False, "error": "catalog_unavailable"}, 503
        return catalog.status(), 200

    def cognitive_head_get(self, graph_id: str) -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        return cognitive.get_head(graph_id)

    def cognitive_dag_get(self, graph_id: str, *, limit: int = 512) -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        return cognitive.get_dag(graph_id, limit=limit)

    def cognitive_commits_get(
        self,
        graph_id: str,
        *,
        since_commit_id: str = "",
        limit: int = 256,
    ) -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        return cognitive.get_commits_for_pull(
            graph_id,
            since_commit_id=since_commit_id,
            limit=limit,
        )

    def cognitive_commits_post(self, data: Dict[str, Any]) -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        graph_id = str((data or {}).get("graph_id") or "")
        commits = (data or {}).get("commits") or []
        if not graph_id:
            return {"ok": False, "error": "missing_graph_id"}, 400
        payload = cognitive.ingest_commits(graph_id, commits if isinstance(commits, list) else [])
        return payload, 200

    def cognitive_publish(self, data: Dict[str, Any]) -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        try:
            from protocol.models import Commit, Graph, Manifest
        except ImportError:
            from cnexus_protocol.models import Commit, Graph, Manifest
        graph_row = (data or {}).get("graph") or {}
        commit_row = (data or {}).get("commit") or {}
        if not graph_row or not commit_row:
            return {"ok": False, "error": "missing_graph_or_commit"}, 400
        graph = Graph.from_dict(graph_row)
        commit = Commit.from_dict(commit_row)
        manifest_row = (data or {}).get("manifest")
        manifest = Manifest.from_dict(manifest_row) if manifest_row else None
        chunk_hashes = (data or {}).get("chunk_hashes") or []
        chunk_payloads = (data or {}).get("chunks") or []
        size = int((data or {}).get("size") or 0)
        payload = cognitive.publish(
            graph,
            commit,
            manifest=manifest,
            chunk_hashes=chunk_hashes,
            chunk_payloads=chunk_payloads if isinstance(chunk_payloads, list) else [],
            size=size,
        )
        self._hooks.audit_event(
            "cognitive.publish",
            {
                "graph_id": graph.graph_id,
                "commit_id": commit.commit_id,
                "root_hash": payload.get("root_hash"),
            },
        )
        return payload, 200

    def storage_manifest_get(self, *, root_hash: str = "", commit_id: str = "") -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        return cognitive.get_manifest(root_hash=root_hash, commit_id=commit_id)

    def storage_chunk_put(self, data: Dict[str, Any]) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        import base64

        raw = (data or {}).get("bytes") or (data or {}).get("content") or b""
        if isinstance(raw, str):
            raw = base64.b64decode(raw.encode("ascii"))
        expected = str((data or {}).get("hash") or (data or {}).get("chunk_hash") or "")
        descriptor = (data or {}).get("descriptor") if isinstance((data or {}).get("descriptor"), dict) else None
        created_by = str((data or {}).get("created_by") or self._hooks.identity_pubkey() or "")
        payload, status = storage.put_chunk(
            raw,
            expected_hash=expected,
            created_by=created_by,
            verifier_peer_id=created_by,
            descriptor=descriptor,
        )
        if status == 200:
            self._hooks.audit_event("storage.chunk.put", {"chunk_hash": payload.get("hash") or payload.get("chunk_hash")})
        return payload, status

    def storage_chunk_state(self, chunk_hash: str) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        return storage.chunk_state(chunk_hash)

    def storage_chunk_get(self, chunk_hash: str) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        return storage.chunk_transfer_get(chunk_hash)

    def storage_chunk_pull(self, data: Dict[str, Any]) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        peer_host = str((data or {}).get("peer_host") or (data or {}).get("host") or "")
        chunk_hash = str((data or {}).get("hash") or (data or {}).get("chunk_hash") or "")
        if not peer_host or not chunk_hash:
            return {"ok": False, "error": "missing_peer_host_or_hash"}, 400
        verifier = str(self._hooks.identity_pubkey() or "local")
        report = storage.pull_chunk_from_peer(peer_host, chunk_hash, verifier_peer_id=verifier)
        status = 200 if report.get("ok") else 502
        if report.get("ok"):
            self._hooks.audit_event(
                "storage.chunk.pull",
                {"chunk_hash": chunk_hash, "peer_host": peer_host},
            )
        return report, status

    def storage_chunk_has(self, chunk_hash: str) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        return storage.chunk_has(chunk_hash)

    def storage_chunk_verify(self, chunk_hash: str, *, content: bytes = b"") -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        return storage.chunk_verify(chunk_hash, content=content or None)

    def storage_manifest_verify(self, data: Dict[str, Any]) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        root_hash = str((data or {}).get("root_hash") or "")
        commit_id = str((data or {}).get("commit_id") or "")
        return storage.verify_manifest_binding(root_hash=root_hash, commit_id=commit_id)

    def storage_status(self) -> JsonResponse:
        storage = self._hooks.get_storage_service()
        if storage is None:
            return {"ok": False, "error": "storage_unavailable"}, 503
        return storage.status(), 200

    def repair_diff_get(
        self,
        *,
        root_hash: str = "",
        commit_id: str = "",
        scope: str = "manifest",
    ) -> JsonResponse:
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        return repair.detect_missing(root_hash=root_hash, commit_id=commit_id, scope=scope)

    def repair_plan_post(self, data: Dict[str, Any]) -> JsonResponse:
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        sources = (data or {}).get("sources") or []
        return repair.generate_plan(
            root_hash=str((data or {}).get("root_hash") or ""),
            commit_id=str((data or {}).get("commit_id") or ""),
            sources=sources if isinstance(sources, list) else [],
            scope=str((data or {}).get("scope") or "manifest"),
        )

    def repair_execute_post(self, data: Dict[str, Any]) -> JsonResponse:
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        sources = (data or {}).get("sources") or []
        plans = (data or {}).get("plans")
        suggested = (data or {}).get("suggested_sources") or []
        confirm = bool((data or {}).get("confirm") or (data or {}).get("user_confirmed"))
        policy_row = (data or {}).get("policy") if isinstance((data or {}).get("policy"), dict) else None
        verifier = str(self._hooks.identity_pubkey() or "local")
        payload, status = repair.execute(
            plans=plans if isinstance(plans, list) else None,
            root_hash=str((data or {}).get("root_hash") or ""),
            commit_id=str((data or {}).get("commit_id") or ""),
            sources=sources if isinstance(sources, list) else [],
            suggested_sources=suggested if isinstance(suggested, list) else [],
            verifier_peer_id=verifier,
            max_concurrent=int((data or {}).get("max_concurrent") or 0),
            max_plans=int((data or {}).get("max_plans") or 0),
            user_confirmed=confirm,
            policy_row=policy_row,
        )
        if payload.get("repaired"):
            self._hooks.audit_event(
                "storage.repair.execute",
                {"repaired": payload.get("repaired"), "executed": payload.get("executed")},
            )
        return payload, status

    def repair_hook_post(self, data: Dict[str, Any]) -> JsonResponse:
        """Observability-only hook — suggested sources, no execute."""
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        peer_host = str((data or {}).get("peer_host") or (data or {}).get("host") or "")
        peer_id = str((data or {}).get("peer_id") or (data or {}).get("pubkey") or "")
        probe = bool((data or {}).get("probe_sources", True))
        include_gate = bool((data or {}).get("include_gate", True))
        reg = self._hooks.get_peer_registry()
        return repair.build_connect_hook(
            peer_host=peer_host,
            peer_id=peer_id,
            peer_registry=reg,
            probe_sources=probe,
            include_gate=include_gate,
        ), 200

    def repair_policy_get(self) -> JsonResponse:
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        return repair.get_execution_policy()

    def repair_policy_post(self, data: Dict[str, Any]) -> JsonResponse:
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        row = (data or {}).get("policy") if isinstance((data or {}).get("policy"), dict) else (data or {})
        return repair.set_execution_policy(row)

    def repair_gate_post(self, data: Dict[str, Any]) -> JsonResponse:
        repair = self._hooks.get_repair_service()
        if repair is None:
            return {"ok": False, "error": "repair_unavailable"}, 503
        return repair.evaluate_gate(
            plans=(data or {}).get("plans") if isinstance((data or {}).get("plans"), list) else None,
            suggested_sources=(data or {}).get("suggested_sources") if isinstance((data or {}).get("suggested_sources"), list) else None,
            user_confirmed=bool((data or {}).get("confirm") or (data or {}).get("user_confirmed")),
            policy_row=(data or {}).get("policy") if isinstance((data or {}).get("policy"), dict) else None,
        )

    def cognitive_status(self) -> JsonResponse:
        cognitive = self._hooks.get_cognitive_service()
        if cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}, 503
        return cognitive.status(), 200

    def application_status(self) -> JsonResponse:
        app = self._hooks.get_application_service()
        if app is None:
            return {"ok": False, "error": "application_unavailable"}, 503
        return app.status(), 200

    def application_publish(self, data: Dict[str, Any]) -> JsonResponse:
        app = self._hooks.get_application_service()
        if app is None:
            return {"ok": False, "error": "application_unavailable"}, 503
        try:
            from protocol.models import Commit, Graph, Manifest
        except ImportError:
            from cnexus_protocol.models import Commit, Graph, Manifest
        row = data or {}
        if row.get("memory") or row.get("block_ids") is not None:
            payload = app.publish_memory(
                block_ids=row.get("block_ids"),
                graph_id=str(row.get("graph_id") or ""),
                topic=str(row.get("topic") or "memory/local"),
                parent_commit=str(row.get("parent_commit") or ""),
            )
            if payload.get("ok"):
                self._hooks.audit_event(
                    "application.publish_memory",
                    {"graph_id": payload.get("graph_id"), "commit_id": payload.get("commit_id")},
                )
            return payload, 200 if payload.get("ok") else 400

        graph_row = row.get("graph") or {}
        commit_row = row.get("commit") or {}
        if not graph_row or not commit_row:
            return {"ok": False, "error": "missing_graph_or_commit"}, 400
        graph = Graph.from_dict(graph_row)
        commit = Commit.from_dict(commit_row)
        manifest_row = row.get("manifest")
        manifest = Manifest.from_dict(manifest_row) if manifest_row else None
        payload = app.publish(
            graph,
            commit,
            manifest=manifest,
            chunk_hashes=row.get("chunk_hashes") or [],
            chunk_payloads=row.get("chunks") or [],
            size=int(row.get("size") or 0),
        )
        if payload.get("ok"):
            self._hooks.audit_event(
                "application.publish",
                {"graph_id": graph.graph_id, "commit_id": commit.commit_id},
            )
        return payload, 200 if payload.get("ok") else 400

    def application_find(self, data: Dict[str, Any]) -> JsonResponse:
        app = self._hooks.get_application_service()
        if app is None:
            return {"ok": False, "error": "application_unavailable"}, 503
        row = data or {}
        payload = app.find(
            graph_id=str(row.get("graph_id") or ""),
            topic=str(row.get("topic") or ""),
            owner=str(row.get("owner") or ""),
            limit=int(row.get("limit") or 64),
        )
        return payload, 200 if payload.get("ok") else 503

    def application_sync(self, data: Dict[str, Any]) -> JsonResponse:
        app = self._hooks.get_application_service()
        if app is None:
            return {"ok": False, "error": "application_unavailable"}, 503
        row = data or {}
        host = str(row.get("host") or row.get("peer_host") or "")
        peer_id = str(row.get("peer_id") or "")
        if not host:
            return {"ok": False, "error": "missing_peer_host"}, 400
        payload = app.sync(host, peer_id=peer_id)
        return payload, 200 if payload.get("ok") else 502

    def application_diagnose(self, data: Dict[str, Any]) -> JsonResponse:
        app = self._hooks.get_application_service()
        if app is None:
            return {"ok": False, "error": "application_unavailable"}, 503
        scope = str((data or {}).get("scope") or "all")
        return app.diagnose(scope=scope), 200

    def application_repair(self, data: Dict[str, Any]) -> JsonResponse:
        app = self._hooks.get_application_service()
        if app is None:
            return {"ok": False, "error": "application_unavailable"}, 503
        row = data or {}
        return app.repair(
            str(row.get("action") or "hook"),
            peer_host=str(row.get("host") or row.get("peer_host") or ""),
            peer_id=str(row.get("peer_id") or ""),
            plans=row.get("plans") if isinstance(row.get("plans"), list) else None,
            suggested_sources=row.get("suggested_sources") if isinstance(row.get("suggested_sources"), list) else None,
            confirm=bool(row.get("confirm") or row.get("user_confirmed")),
            probe_sources=bool(row.get("probe_sources", True)),
            include_gate=bool(row.get("include_gate", True)),
            user_confirmed=bool(row.get("confirm") or row.get("user_confirmed")),
        )

    def network_firewall_ban(self, data: Dict[str, Any]) -> JsonResponse:
        fw = self._hooks.get_network_firewall()
        if fw is None:
            return {"ok": False, "error": "firewall_unavailable"}, 503
        peer_id = str((data or {}).get("peer_id") or (data or {}).get("pubkey") or "")
        reason = str((data or {}).get("reason") or "manual_ban")
        if not peer_id:
            return {"ok": False, "error": "missing_peer_id"}, 400
        result = fw.ban_peer(peer_id, reason=reason, source="api")
        reg = self._hooks.get_peer_registry()
        dht = self._hooks.get_dht_service()
        if reg:
            reg.remove_peer(peer_id)
        if dht and hasattr(dht, "_buckets"):
            with dht._lock:
                for bucket in dht._buckets.values():
                    bucket.pop(peer_id, None)
        return result, 200
