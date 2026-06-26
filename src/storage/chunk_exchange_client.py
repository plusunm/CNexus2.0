"""HTTP client for P4.5 chunk state alignment and transfer."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict
from urllib import parse as urlparse
from urllib import request as urlrequest


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def _get_json(url: str, *, timeout: float = 12.0) -> Dict[str, Any]:
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


def fetch_chunk_state(peer_host: str, chunk_hash: str, *, timeout: float = 8.0) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    query = urlparse.urlencode({"hash": chunk_hash})
    return _get_json(f"{host}/api/storage/chunk/state?{query}", timeout=timeout)


def fetch_chunk(peer_host: str, chunk_hash: str, *, timeout: float = 20.0) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    query = urlparse.urlencode({"hash": chunk_hash})
    return _get_json(f"{host}/api/storage/chunk?{query}", timeout=timeout)


def push_chunk(
    peer_host: str,
    chunk_hash: str,
    content: bytes,
    *,
    descriptor: Dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    payload: Dict[str, Any] = {
        "hash": chunk_hash,
        "bytes": base64.b64encode(content).decode("ascii"),
    }
    if descriptor:
        payload["descriptor"] = descriptor
    return _post_json(f"{host}/api/storage/chunk", payload, timeout=timeout)


def decode_chunk_bytes(payload: Dict[str, Any]) -> bytes:
    raw = payload.get("bytes") or payload.get("content") or b""
    if isinstance(raw, str):
        return base64.b64decode(raw.encode("ascii"))
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return b""
