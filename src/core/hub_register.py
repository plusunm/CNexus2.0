"""Client-side hub registration — report local node to rendezvous."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest

from .founder_peers import HUB_HOST


def _normalize_host(host: str) -> str:
    host = str(host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def _hub_register_enabled() -> bool:
    raw = os.environ.get("CNEXUS_HUB_REGISTER", "1")
    return raw.lower() not in ("0", "false", "no", "")


def _hub_register_interval() -> float:
    try:
        return max(60.0, float(os.environ.get("CNEXUS_HUB_REGISTER_INTERVAL", "300")))
    except ValueError:
        return 300.0


def collect_registration_endpoints(connectivity_manager, *, local_port: int = 7864) -> Tuple[str, List[str]]:
    """Pick best host + endpoint list from connectivity candidates."""
    host = ""
    endpoints: List[str] = []
    if connectivity_manager is None:
        return "", endpoints
    try:
        connectivity_manager.gather_candidates(refresh_stun=True)
        status = connectivity_manager.status() or {}
    except Exception:
        status = {}
    public = _normalize_host(str(status.get("public_url") or ""))
    if public:
        host = public
        endpoints.append(public)
    for cand in list(status.get("candidates") or []):
        url = _normalize_host(str(cand.get("url") or ""))
        if not url or url in endpoints:
            continue
        endpoints.append(url)
        kind = str(cand.get("type") or "")
        if not host and kind in ("host", "srflx"):
            host = url
    if not host and endpoints:
        host = endpoints[0]
    if not host:
        host = f"http://127.0.0.1:{int(local_port)}"
        if host not in endpoints:
            endpoints.insert(0, host)
    return host, endpoints


def post_hub_registration(
    hub_base: str,
    *,
    identity_manager,
    build_signed_headers: Callable[..., Dict[str, str]],
    host: str,
    endpoints: Optional[List[str]] = None,
    label: str = "",
    timeout: float = 8.0,
) -> dict:
    hub = _normalize_host(hub_base)
    if not hub or identity_manager is None:
        return {"ok": False, "error": "hub_or_identity_unavailable"}
    body = {
        "host": _normalize_host(host),
        "endpoints": [_normalize_host(u) for u in (endpoints or []) if _normalize_host(u)],
        "label": str(label or "").strip(),
    }
    headers = build_signed_headers(identity_manager, body)
    headers["Content-Type"] = "application/json"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    url = f"{hub}/api/connectivity/register"
    try:
        req = urlrequest.Request(url, data=data, method="POST", headers=headers)
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if isinstance(payload, dict):
            return payload
        return {"ok": False, "error": "invalid_response"}
    except urlerror.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"ok": False, "error": f"http_{exc.code}"}
        return payload if isinstance(payload, dict) else {"ok": False, "error": f"http_{exc.code}"}
    except (urlerror.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


def register_local_node_with_hub(
    hub_base: str,
    *,
    identity_manager,
    build_signed_headers: Callable[..., Dict[str, str]],
    connectivity_manager=None,
    local_port: int = 7864,
    label: str = "client",
) -> dict:
    host, endpoints = collect_registration_endpoints(connectivity_manager, local_port=local_port)
    return post_hub_registration(
        hub_base,
        identity_manager=identity_manager,
        build_signed_headers=build_signed_headers,
        host=host,
        endpoints=endpoints,
        label=label,
    )


def schedule_hub_registration(
    hub_base: str,
    *,
    identity_manager,
    build_signed_headers: Callable[..., Dict[str, str]],
    connectivity_manager=None,
    local_port: int = 7864,
    delay_s: float = 12.0,
) -> None:
    if not _hub_register_enabled():
        return
    hub = _normalize_host(hub_base or HUB_HOST)
    if not hub or identity_manager is None:
        return

    def _loop():
        time.sleep(max(0.0, float(delay_s)))
        interval = _hub_register_interval()
        while True:
            try:
                register_local_node_with_hub(
                    hub,
                    identity_manager=identity_manager,
                    build_signed_headers=build_signed_headers,
                    connectivity_manager=connectivity_manager,
                    local_port=local_port,
                )
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=_loop, name="cnexus-hub-register", daemon=True).start()
