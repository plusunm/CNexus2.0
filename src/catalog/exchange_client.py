"""HTTP client for Catalog Layer peer exchange (P2.1)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def _get_json(url: str, *, timeout: float = 8.0) -> Dict[str, Any]:
    req = urlrequest.Request(url, method="GET")
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _post_json(url: str, payload: dict, *, timeout: float = 12.0) -> Dict[str, Any]:
    body = json.dumps(payload or {}).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_generation(peer_host: str, *, timeout: float = 8.0) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    return _get_json(f"{host}/api/catalog/generation", timeout=timeout)


def fetch_bloom_summary(peer_host: str, *, namespace: str = "catalog/system", timeout: float = 8.0) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    query = urlparse.urlencode({"namespace": namespace})
    return _get_json(f"{host}/api/catalog/bloom/summary?{query}", timeout=timeout)


def exchange_bloom(
    peer_host: str,
    local_bloom_b64: str,
    *,
    namespace: str = "catalog/system",
    summary: Mapping[str, Any] | None = None,
    interest: Mapping[str, Any] | None = None,
    timeout: float = 12.0,
) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    payload: Dict[str, Any] = {
        "bloom": local_bloom_b64,
        "action": "exchange",
        "namespace": namespace,
    }
    if summary:
        payload["summary"] = dict(summary)
    if interest:
        payload["interest"] = dict(interest)
    return _post_json(f"{host}/api/catalog/bloom", payload, timeout=timeout)


def exchange_index(
    peer_host: str,
    *,
    commit_cursors: Mapping[str, str] | None = None,
    entries: List[dict],
    interest: Mapping[str, Any] | None = None,
    namespace: str = "catalog/system",
    limit: int = 256,
    timeout: float = 12.0,
) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    payload: Dict[str, Any] = {
        "commit_cursors": dict(commit_cursors or {}),
        "since_commit_cursors": dict(commit_cursors or {}),
        "entries": entries,
        "limit": int(limit),
        "action": "exchange",
        "namespace": namespace,
    }
    if interest:
        payload["interest"] = dict(interest)
    return _post_json(f"{host}/api/catalog/index", payload, timeout=timeout)
