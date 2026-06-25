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

    def connectivity_connect(self, peer_id: str) -> JsonResponse:
        cm = self._hooks.get_connectivity_manager()
        if cm is None:
            return {"ok": False, "error": "connectivity_unavailable"}, 503
        peer_id = str(peer_id or "").strip()
        if not peer_id:
            return {"ok": False, "error": "missing_peer_id"}, 400
        report = cm.connect_to(peer_id)
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
            gossip.schedule_check(url, peer_pubkey=peer_id, genesis=True)

        if handler and url and not handshake_report.get("ok") and not handshake_report.get("skipped"):
            report["ok"] = False
            report["error"] = str(handshake_report.get("error") or "handshake_failed")
            return report, 502

        return report, 200

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
