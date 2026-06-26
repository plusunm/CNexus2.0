"""LAN peer discovery — locate CNexus nodes by device ID without manual host config."""

from __future__ import annotations

import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest


IdentityProbeFn = Callable[[str, float], Optional[str]]


def _normalize_pubkey(value: str) -> str:
    return str(value or "").strip().lower()


def _subnet_hosts(ip: str) -> List[str]:
    parts = str(ip or "").split(".")
    if len(parts) != 4:
        return []
    try:
        ints = [int(p) for p in parts]
    except ValueError:
        return []
    if ints[0] == 10 or (ints[0] == 172 and 16 <= ints[1] <= 31) or ints[0] == 192 and ints[1] == 168:
        base = ".".join(parts[:3])
        return [f"{base}.{host}" for host in range(1, 255)]
    return []


def default_identity_probe(url: str, timeout: float = 0.35) -> Optional[str]:
    base = str(url or "").strip().rstrip("/")
    if not base:
        return None
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    endpoint = f"{base}/api/connectivity/identity"
    try:
        req = urlrequest.Request(endpoint, method="GET")
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        if not payload.get("ok"):
            return None
        pubkey = _normalize_pubkey(str(payload.get("pubkey") or ""))
        return pubkey or None
    except (urlerror.URLError, urlerror.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None


def scan_lan_cnexus_nodes(
    *,
    port: int = 7864,
    local_ips: Optional[List[str]] = None,
    timeout: float = 0.35,
    max_workers: int = 48,
    probe: Optional[IdentityProbeFn] = None,
) -> List[Dict[str, str]]:
    """Return CNexus peers visible on local subnets: [{pubkey, host, url}, ...]."""
    probe = probe or default_identity_probe
    if local_ips is None:
        try:
            from network.host_config import list_lan_ipv4
        except ImportError:
            from host_config import list_lan_ipv4
        local_ips = list_lan_ipv4()

    targets: List[str] = []
    seen_hosts: set[str] = set()
    for ip in local_ips or []:
        for host in _subnet_hosts(ip):
            if host in seen_hosts:
                continue
            seen_hosts.add(host)
            targets.append(host)

    if not targets:
        return []

    found: Dict[str, Dict[str, str]] = {}

    def _check(host: str) -> Optional[Dict[str, str]]:
        url = f"http://{host}:{int(port)}"
        pubkey = probe(url, timeout)
        if not pubkey:
            return None
        return {"pubkey": pubkey, "host": url, "url": url}

    workers = max(8, min(max_workers, len(targets)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_check, host): host for host in targets}
        for future in as_completed(futures):
            try:
                row = future.result()
            except Exception:
                continue
            if row and row["pubkey"] not in found:
                found[row["pubkey"]] = row
    return list(found.values())


def find_peer_on_lan(
    target_pubkey: str,
    *,
    port: int = 7864,
    local_ips: Optional[List[str]] = None,
    timeout: float = 0.35,
    probe: Optional[IdentityProbeFn] = None,
) -> Optional[str]:
    """Return gateway URL for target_pubkey if found on LAN, else None."""
    target = _normalize_pubkey(target_pubkey)
    if not target:
        return None
    for row in scan_lan_cnexus_nodes(
        port=port,
        local_ips=local_ips,
        timeout=timeout,
        probe=probe,
    ):
        if _normalize_pubkey(row.get("pubkey") or "") == target:
            return str(row.get("url") or row.get("host") or "")
    return None
