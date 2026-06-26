"""HTTP client for Cognitive Layer commit pull/push."""

from __future__ import annotations

import json
from typing import Any, Dict, List
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


def fetch_head(peer_host: str, graph_id: str, *, timeout: float = 8.0) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    query = urlparse.urlencode({"graph_id": graph_id})
    return _get_json(f"{host}/api/cognitive/head?{query}", timeout=timeout)


def fetch_commits(
    peer_host: str,
    graph_id: str,
    *,
    since_commit_id: str = "",
    limit: int = 256,
    timeout: float = 12.0,
) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    query = urlparse.urlencode(
        {
            "graph_id": graph_id,
            "since_commit_id": since_commit_id,
            "limit": str(int(limit)),
        }
    )
    return _get_json(f"{host}/api/cognitive/commits?{query}", timeout=timeout)


def push_commits(
    peer_host: str,
    graph_id: str,
    commits: List[dict],
    *,
    timeout: float = 12.0,
) -> Dict[str, Any]:
    host = _normalize_host(peer_host)
    return _post_json(
        f"{host}/api/cognitive/commits",
        {"graph_id": graph_id, "commits": commits},
        timeout=timeout,
    )
