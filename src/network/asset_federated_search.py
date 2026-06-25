"""Federated asset + memory search: local, trusted mesh, and DHT-wide scopes."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

SEARCH_SCOPES = ("local", "trusted", "network")


def normalize_scope(scope: str) -> str:
    value = str(scope or "local").strip().lower()
    return value if value in SEARCH_SCOPES else "local"


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def trusted_peer_pubkeys(peer_registry) -> Set[str]:
    if peer_registry is None:
        return set()
    out: Set[str] = set()
    for pubkey, row in peer_registry.get_all_peers().items():
        if str(row.get("status") or "").strip() in ("trusted", "online"):
            out.add(str(pubkey))
    return out


def iter_remote_targets(scope: str, peer_registry, dht_service) -> List[Tuple[str, str]]:
    """Peers to query for federated search as (pubkey, host)."""
    scope = normalize_scope(scope)
    if scope == "local":
        return []

    seen_hosts: Set[str] = set()
    rows: List[Tuple[str, str]] = []

    def add(pubkey: str, host: str) -> None:
        normalized = _normalize_host(host)
        if not normalized or normalized in seen_hosts:
            return
        seen_hosts.add(normalized)
        rows.append((str(pubkey or ""), normalized))

    if peer_registry is not None:
        for pubkey, meta in peer_registry.get_all_peers().items():
            status = str(meta.get("status") or "").strip()
            if scope == "trusted" and status not in ("trusted", "online"):
                continue
            add(pubkey, str(meta.get("host") or ""))

    if scope == "network" and dht_service is not None:
        lock = getattr(dht_service, "_lock", None)
        buckets = getattr(dht_service, "_buckets", {}) or {}
        if lock:
            with lock:
                for bucket in buckets.values():
                    for row in bucket.values():
                        add(str(row.get("pubkey") or ""), str(row.get("host") or ""))
        else:
            for bucket in buckets.values():
                for row in bucket.values():
                    add(str(row.get("pubkey") or ""), str(row.get("host") or ""))
        for host in getattr(dht_service, "bootstrap_hosts", []) or []:
            add("", str(host))

    return rows


def _origin_matches_scope(source_peer: str, scope: str, trusted: Set[str]) -> bool:
    scope = normalize_scope(scope)
    peer = str(source_peer or "").strip()
    if scope == "local":
        return not peer
    if scope == "trusted":
        return not peer or peer in trusted
    return True


def filter_rows_by_scope(rows: List[dict], scope: str, trusted: Set[str]) -> List[dict]:
    scope = normalize_scope(scope)
    if scope == "network":
        return list(rows)
    out: List[dict] = []
    for row in rows:
        peer = str(row.get("source_peer") or "").strip()
        if _origin_matches_scope(peer, scope, trusted):
            out.append(row)
    return out


def search_memory_blocks(
    memory_store,
    query: str,
    *,
    scope: str = "local",
    trusted: Optional[Set[str]] = None,
    limit: int = 20,
) -> List[dict]:
    """Search in-memory blocks; always local copies, filtered by origin scope.

    Deprecated for gateway use — prefer ``MemoryAssetService.search_memory_rows``
    (Memory Domain) which delegates to ``MemoryQueryService.search_block_rows``.
    """
    query = str(query or "").strip().lower()
    if not query or memory_store is None:
        return []
    trusted = trusted or set()
    scope = normalize_scope(scope)
    hits: List[dict] = []
    blocks = list(getattr(memory_store, "blocks", []) or [])
    for block in reversed(blocks):
        data = dict(block.get("data") or {})
        source_peer = str(data.get("source_peer") or "").strip()
        if not _origin_matches_scope(source_peer, scope, trusted):
            continue
        block_id = str(block.get("block_id") or "")
        content = str(data.get("content") or data.get("content_preview") or "")
        haystack = " ".join(
            str(part or "")
            for part in (block_id, content, data.get("tag"), data.get("title"), data.get("filename"))
        ).lower()
        if query not in haystack:
            continue
        hits.append(
            {
                "kind": "memory",
                "block_id": block_id,
                "asset_id": str(data.get("asset_id") or ""),
                "type": "memory",
                "filename": data.get("filename") or data.get("title") or block_id[:16],
                "summary": content[:160] or block_id[:48],
                "desc": str(data.get("tag") or data.get("meta") or ""),
                "source_peer": source_peer or None,
                "peer_host": None,
                "local_blob": True,
                "memory_origin": "local" if not source_peer else ("trusted" if source_peer in trusted else "network"),
                "score": 1.0,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def remote_semantic_search(
    host: str,
    query: str,
    *,
    source_pubkey: str = "",
    kind: Optional[str] = None,
    limit: int = 8,
    build_signed_headers: Optional[Callable] = None,
    identity_manager=None,
    timeout: float = 12,
) -> List[dict]:
    host = _normalize_host(host)
    query = str(query or "").strip()
    if not host or not query:
        return []

    params: Dict[str, str] = {
        "q": query,
        "scope": "local",
        "limit": str(max(1, min(int(limit), 20))),
    }
    if kind:
        params["kind"] = kind
    url = f"{host}/api/asset/search/semantic?{urlparse.urlencode(params)}"
    headers = {"Content-Type": "application/json"}
    if identity_manager is not None and build_signed_headers is not None:
        headers.update(build_signed_headers(identity_manager, {"q": query, "scope": "local"}))

    req = urlrequest.Request(url, headers=headers, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urlerror.HTTPError:
        return []
    except Exception:
        return []

    if not payload.get("ok"):
        return []

    rows: List[dict] = []
    for hit in payload.get("hits") or []:
        if not isinstance(hit, dict):
            continue
        row = dict(hit)
        row["source_peer"] = source_pubkey or row.get("source_peer")
        row["peer_host"] = host
        row["local_blob"] = False
        row["kind"] = row.get("kind") or "asset"
        row["memory_origin"] = "trusted" if source_pubkey else "network"
        rows.append(row)
    return rows


def merge_search_hits(*groups: List[dict], limit: int = 30) -> List[dict]:
    merged: List[dict] = []
    seen: Set[str] = set()

    def key(row: dict) -> str:
        asset_id = str(row.get("asset_id") or "").strip()
        if asset_id:
            return f"asset:{asset_id}"
        block_id = str(row.get("block_id") or "").strip()
        if block_id:
            return f"memory:{block_id}"
        return f"row:{len(seen)}"

    for group in groups:
        for row in group:
            dedupe = key(row)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            merged.append(row)

    merged.sort(key=lambda row: float(row.get("score") or 0), reverse=True)
    return merged[: max(1, limit)]


def federated_semantic_search(
    local_hits: List[dict],
    *,
    query: str,
    scope: str,
    peer_registry,
    dht_service,
    kind: Optional[str] = None,
    limit: int = 20,
    build_signed_headers: Optional[Callable] = None,
    identity_manager=None,
) -> Tuple[List[dict], dict]:
    scope = normalize_scope(scope)
    trusted = trusted_peer_pubkeys(peer_registry)
    local_filtered = filter_rows_by_scope(local_hits, scope, trusted)

    remote_groups: List[List[dict]] = []
    targets = iter_remote_targets(scope, peer_registry, dht_service)
    per_peer = max(3, min(8, limit // max(len(targets), 1) + 2))

    for pubkey, host in targets:
        remote_groups.append(
            remote_semantic_search(
                host,
                query,
                source_pubkey=pubkey,
                kind=kind,
                limit=per_peer,
                build_signed_headers=build_signed_headers,
                identity_manager=identity_manager,
            )
        )

    merged = merge_search_hits(local_filtered, *remote_groups, limit=limit)
    for row in merged:
        if not row.get("memory_origin"):
            peer = str(row.get("source_peer") or "").strip()
            if not peer:
                row["memory_origin"] = "local"
            elif peer in trusted:
                row["memory_origin"] = "trusted"
            else:
                row["memory_origin"] = "network"

    report = {
        "scope": scope,
        "local_count": len(local_filtered),
        "remote_peers_queried": len(targets),
        "remote_hit_count": sum(len(group) for group in remote_groups),
        "merged_count": len(merged),
    }
    return merged, report
