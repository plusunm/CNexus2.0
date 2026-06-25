"""Inbound peer trust gate — trusted registry required after signature auth."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Tuple

HEADER_PUBKEY = "X-CNexus-Pubkey"
ASSET_ID_RE = re.compile(r"^[a-f0-9]{64}$")

# POST routes that require a trusted peer (after Ed25519 auth).
TRUSTED_INBOUND_POST_PATHS = frozenset({
    "/api/peer/sync",
    "/api/peer/negotiate",
    "/api/asset/receive",
})

# GET routes that expose audit deltas to peers.
TRUSTED_INBOUND_GET_PATHS = frozenset({
    "/api/peer/audit",
    "/api/peer/audit-proof",
})

TRUSTED_PEER_STATUSES = frozenset({"trusted", "online"})


def is_asset_content_get(path: str, body: dict | None) -> bool:
    normalized = (path or "/").rstrip("/") or "/"
    if not normalized.startswith("/api/asset/"):
        return False
    asset_id = normalized[len("/api/asset/") :].strip("/")
    if not ASSET_ID_RE.fullmatch(asset_id):
        return False
    payload = body if isinstance(body, dict) else {}
    content = payload.get("content")
    raw = payload.get("raw")
    if content in (1, "1", True):
        return True
    if raw in (1, "1", True):
        return True
    if isinstance(content, str) and content.lower() in ("1", "true", "yes"):
        return True
    if isinstance(raw, str) and raw.lower() in ("1", "true", "yes"):
        return True
    return False


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def peer_trust_required() -> bool:
    """When false, inbound peer trust gate is skipped (dev / tests)."""
    return _env_truthy("CNEXUS_PEER_TRUST_REQUIRED", default=True)


def path_requires_trusted_peer(path: str, method: str = "POST", *, body: dict | None = None) -> bool:
    normalized = (path or "/").rstrip("/") or "/"
    if normalized == "/api/p2p/handshake":
        return False
    if method.upper() == "GET":
        if normalized in TRUSTED_INBOUND_GET_PATHS:
            return True
        return is_asset_content_get(path, body)
    return normalized in TRUSTED_INBOUND_POST_PATHS


def _header_pubkey(headers) -> str:
    if hasattr(headers, "get"):
        return str(headers.get(HEADER_PUBKEY) or headers.get(HEADER_PUBKEY.lower()) or "").strip()
    return ""


def is_trusted_peer_pubkey(peer_registry, pubkey: str) -> bool:
    if peer_registry is None:
        return False
    checker = getattr(peer_registry, "is_trusted_peer", None)
    if callable(checker):
        return bool(checker(pubkey))
    row = peer_registry.get_peer(pubkey)
    if not row:
        return False
    return str(row.get("status") or "").strip() in TRUSTED_PEER_STATUSES


def verify_inbound_peer_trust(
    path: str,
    headers,
    peer_registry,
    *,
    method: str = "POST",
    body: dict | None = None,
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Require caller pubkey to be in the trusted peer registry.
    Returns (ok, error_body, http_status).
    """
    if not peer_trust_required():
        return True, {}, 200
    if not path_requires_trusted_peer(path, method, body=body):
        return True, {}, 200

    pubkey = _header_pubkey(headers)
    if not pubkey:
        return False, {"error": "Forbidden: Missing Peer Identity", "status": "error"}, 403

    if is_trusted_peer_pubkey(peer_registry, pubkey):
        return True, {}, 200

    return False, {
        "error": "Forbidden: Untrusted Peer",
        "status": "error",
        "message": "Peer not in trusted registry — complete P2P handshake first",
        "peer_pubkey": pubkey[:16] + "…" if len(pubkey) > 16 else pubkey,
    }, 403


def peer_trust_status(peer_registry) -> Dict[str, Any]:
    peers = peer_registry.get_all_peers() if peer_registry else {}
    trusted = [
        pubkey
        for pubkey, row in peers.items()
        if str(row.get("status") or "").strip() in TRUSTED_PEER_STATUSES
    ]
    return {
        "required": peer_trust_required(),
        "trusted_count": len(trusted),
        "strict_post_paths": sorted(TRUSTED_INBOUND_POST_PATHS),
        "strict_get_paths": sorted(TRUSTED_INBOUND_GET_PATHS),
    }
