"""Outbound P2P handshake client — establish trust with a remote CNexus peer."""

from __future__ import annotations

import json
from typing import Any, Dict
from urllib import error as urlerror
from urllib import request as urlrequest


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def _post_json(url: str, payload: dict, *, timeout: float = 12) -> Dict[str, Any]:
    body = json.dumps(payload or {}).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def perform_outbound_handshake(
    peer_host: str,
    peer_pubkey: str,
    handshake_handler,
    *,
    local_host: str = "",
    timeout: float = 12,
) -> Dict[str, Any]:
    """
    Run HELLO → CHALLENGE → signed RESPONSE against remote /api/p2p/handshake.
    On success the remote peer adds us to its trusted registry.
    """
    host = _normalize_host(peer_host)
    peer_pubkey = str(peer_pubkey or "").strip()
    local_host = _normalize_host(local_host)
    local_pubkey = handshake_handler.local_pubkey()

    result: Dict[str, Any] = {
        "ok": False,
        "peer_host": host,
        "peer_pubkey": peer_pubkey,
        "local_pubkey": local_pubkey,
        "phase": "init",
    }
    if not host or not peer_pubkey:
        result["error"] = "missing_peer_host_or_pubkey"
        return result

    endpoint = f"{host}/api/p2p/handshake"
    try:
        hello = _post_json(
            endpoint,
            {
                "action": "HELLO",
                "peer_pubkey": local_pubkey,
                "host": local_host,
            },
            timeout=timeout,
        )
    except urlerror.HTTPError as exc:
        result["phase"] = "hello"
        result["error"] = f"http_{exc.code}"
        return result
    except Exception as exc:
        result["phase"] = "hello"
        result["error"] = str(exc)
        return result

    if not hello.get("ok"):
        result["phase"] = "hello"
        result["error"] = str(hello.get("error") or "hello_failed")
        return result

    nonce = str(hello.get("nonce") or "")
    if not nonce:
        result["phase"] = "challenge"
        result["error"] = "missing_nonce"
        return result

    result["phase"] = "challenge"
    response_body = handshake_handler.build_response(nonce, peer_pubkey)
    try:
        done = _post_json(
            endpoint,
            {
                "action": "HANDSHAKE_RESPONSE",
                "peer_pubkey": local_pubkey,
                "host": local_host,
                **response_body,
            },
            timeout=timeout,
        )
    except urlerror.HTTPError as exc:
        result["phase"] = "response"
        result["error"] = f"http_{exc.code}"
        return result
    except Exception as exc:
        result["phase"] = "response"
        result["error"] = str(exc)
        return result

    if not done.get("ok") or done.get("status") != "trusted_peer":
        result["phase"] = "response"
        result["error"] = str(done.get("error") or "handshake_failed")
        return result

    result.update({
        "ok": True,
        "status": "trusted_peer",
        "phase": "complete",
        "remote_trusts_us": True,
        "remote_pubkey": str(done.get("pubkey") or peer_pubkey),
    })
    return result
