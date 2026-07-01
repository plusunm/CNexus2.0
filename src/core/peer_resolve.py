"""Resolve peer pubkey → reachable host (device-ID-only connect)."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional, Tuple
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from .founder_peers import HUB_HOST, bootstrap_host_for_pubkey


def _normalize_host(host: str) -> str:
    host = str(host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def _fetch_hub_resolve(hub_base: str, pubkey: str, *, timeout: float = 5.0) -> str:
    hub = _normalize_host(hub_base)
    pubkey = str(pubkey or "").strip().lower()
    if not hub or not pubkey:
        return ""
    qs = urlparse.urlencode({"pubkey": pubkey})
    url = f"{hub}/api/connectivity/resolve?{qs}"
    try:
        req = urlrequest.Request(url, method="GET")
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not isinstance(payload, dict) or not payload.get("ok"):
            return ""
        return _normalize_host(str(payload.get("host") or ""))
    except (urlerror.URLError, urlerror.HTTPError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return ""


def resolve_peer_host(
    pubkey: str,
    *,
    peer_registry=None,
    local_pubkey: str = "",
    local_public_url: str = "",
    dht_service=None,
    hub_base: str = "",
    remote_resolve: bool = True,
) -> Tuple[str, str]:
    """
    Resolve a device ID to a host URL.
    Returns (host, source) where source is bootstrap|registry|self|hub|dht|"" .
    """
    pubkey = str(pubkey or "").strip().lower()
    if not pubkey:
        return "", ""

    local = str(local_pubkey or "").strip().lower()
    if local and pubkey == local:
        host = _normalize_host(local_public_url)
        return host, "self"

    host = bootstrap_host_for_pubkey(pubkey)
    if host:
        return _normalize_host(host), "bootstrap"

    if peer_registry is not None:
        meta = peer_registry.get_peer(pubkey) or {}
        host = _normalize_host(str(meta.get("host") or ""))
        if host:
            return host, "registry"

    hub = _normalize_host(hub_base or HUB_HOST)
    if remote_resolve and hub:
        host = _fetch_hub_resolve(hub, pubkey)
        if host:
            return host, "hub"

    if dht_service is not None and hasattr(dht_service, "find_node"):
        try:
            node = dht_service.find_node(pubkey)
        except Exception:
            node = None
        if isinstance(node, dict):
            endpoints = list(node.get("endpoints") or [])
            host = _normalize_host(str(node.get("host") or (endpoints[0] if endpoints else "")))
            if host:
                return host, "dht"

    return "", ""


def resolve_for_connect(
    pubkey: str,
    *,
    peer_registry=None,
    local_pubkey: str = "",
    local_public_url: str = "",
    dht_service=None,
) -> Tuple[str, str]:
    """Connect-time resolver (bootstrap → registry → hub directory → DHT)."""
    return resolve_peer_host(
        pubkey,
        peer_registry=peer_registry,
        local_pubkey=local_pubkey,
        local_public_url=local_public_url,
        dht_service=dht_service,
        remote_resolve=True,
    )
