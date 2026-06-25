"""Pull cognitive assets from trusted peers on local cache miss."""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Callable, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

ASSET_ID_RE = re.compile(r"^[a-f0-9]{64}$")


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def resolve_peer_host(peer_registry, source_peer: str) -> str:
    source_peer = str(source_peer or "").strip()
    if not source_peer or peer_registry is None:
        return ""
    row = peer_registry.get_peer(source_peer) or {}
    return _normalize_host(str(row.get("host") or ""))


def fetch_asset_from_peer(
    peer_host: str,
    asset_id: str,
    *,
    identity_manager=None,
    build_signed_headers: Optional[Callable] = None,
    timeout: float = 30,
) -> Dict[str, Any]:
    """GET /api/asset/{id}?content=1 from a trusted remote peer."""
    host = _normalize_host(peer_host)
    asset_id = str(asset_id or "").strip()
    result: Dict[str, Any] = {
        "ok": False,
        "asset_id": asset_id,
        "peer_host": host,
        "phase": "request",
    }
    if not host or not ASSET_ID_RE.fullmatch(asset_id):
        result["error"] = "invalid_peer_or_asset_id"
        return result

    payload = {"asset_id": asset_id, "content": 1}
    headers = {"Content-Type": "application/json"}
    if identity_manager is not None and build_signed_headers is not None:
        headers.update(build_signed_headers(identity_manager, payload))

    req = urlrequest.Request(
        f"{host}/api/asset/{asset_id}?content=1",
        headers=headers,
        method="GET",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            remote = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urlerror.HTTPError as exc:
        result["error"] = f"http_{exc.code}"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result

    if not remote.get("ok"):
        result["error"] = str(remote.get("error") or "fetch_failed")
        return result

    kind = str(remote.get("type") or "code")
    raw: Optional[bytes] = None
    if kind == "code":
        text = str(remote.get("content") or "")
        raw = text.encode("utf-8")
    else:
        b64 = str(remote.get("content_base64") or "")
        if b64:
            try:
                raw = base64.b64decode(b64)
            except Exception:
                result["error"] = "invalid_content_base64"
                return result

    if raw is None:
        result["error"] = "missing_content"
        return result

    result.update({
        "ok": True,
        "phase": "fetched",
        "meta": {
            "id": asset_id,
            "type": kind,
            "filename": remote.get("filename"),
            "summary": remote.get("summary"),
            "desc": remote.get("desc"),
            "size_bytes": remote.get("size_bytes", len(raw)),
        },
        "raw": raw,
    })
    return result


def pull_asset_into_local(
    asset_id: str,
    asset_processor,
    peer_registry,
    *,
    source_peer: str = "",
    peer_host: str = "",
    identity_manager=None,
    build_signed_headers: Optional[Callable] = None,
    try_trusted_fallback: bool = False,
) -> Dict[str, Any]:
    """
    On cache miss, fetch full blob from source_peer (or trusted peers) and ingest locally.
    Verifies SHA-256(asset_id) == content hash before write.
    """
    asset_id = str(asset_id or "").strip()
    report: Dict[str, Any] = {"ok": False, "asset_id": asset_id, "local": False}
    if asset_processor is None:
        report["error"] = "asset_processor_unavailable"
        return report
    if not ASSET_ID_RE.fullmatch(asset_id):
        report["error"] = "invalid_asset_id"
        return report

    blob, meta, status = asset_processor.read_raw(asset_id)
    if blob is not None and status == 200:
        report.update({"ok": True, "local": True, "status": "already_present", "meta": meta})
        return report

    hosts: list[tuple[str, str]] = []
    peer = str(source_peer or "").strip()
    if peer:
        host = resolve_peer_host(peer_registry, peer)
        if host:
            hosts.append((host, peer))

    direct_host = _normalize_host(str(peer_host or ""))
    if direct_host and not any(h == direct_host for h, _ in hosts):
        hosts.append((direct_host, peer or ""))

    if not hosts and try_trusted_fallback and peer_registry is not None:
        for pubkey, row in peer_registry.get_all_peers().items():
            if str(row.get("status") or "") not in ("trusted", "online"):
                continue
            host = _normalize_host(str(row.get("host") or ""))
            if host:
                hosts.append((host, pubkey))

    if not hosts:
        report["error"] = "no_trusted_peer_host"
        return report

    content_hash = getattr(asset_processor, "content_hash", None)
    last_error = "pull_failed"
    for host, pubkey in hosts:
        fetched = fetch_asset_from_peer(
            host,
            asset_id,
            identity_manager=identity_manager,
            build_signed_headers=build_signed_headers,
        )
        if not fetched.get("ok"):
            last_error = str(fetched.get("error") or last_error)
            continue
        raw = fetched.get("raw") or b""
        if callable(content_hash) and content_hash(raw) != asset_id:
            last_error = "hash_mismatch"
            continue
        ingested = asset_processor.ingest_remote(
            {**dict(fetched.get("meta") or {}), "id": asset_id},
            bytes(raw),
            source_peer=pubkey,
        )
        report.update({
            "ok": bool(ingested.get("ok")),
            "status": ingested.get("status"),
            "deduped": ingested.get("deduped"),
            "source_peer": pubkey,
            "peer_host": host,
            "meta": ingested.get("meta") or fetched.get("meta"),
            "pulled": not ingested.get("deduped"),
        })
        return report

    report["error"] = last_error
    return report
