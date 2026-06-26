"""Automatic network binding and public URL resolution for zero-config P2P."""

from __future__ import annotations

import os
import socket
from typing import List


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def auto_network_enabled() -> bool:
    return _env_truthy("CNEXUS_AUTO_NETWORK", True)


def lan_discovery_enabled() -> bool:
    return _env_truthy("CNEXUS_LAN_DISCOVERY", True)


def _normalize_host(host: str) -> str:
    host = (host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def list_lan_ipv4() -> List[str]:
    """Collect non-loopback IPv4 addresses for this machine."""
    seen: set[str] = set()
    ordered: List[str] = []

    def _add(ip: str) -> None:
        ip = str(ip or "").strip()
        if not ip or ip.startswith("127.") or ip in seen:
            return
        seen.add(ip)
        ordered.append(ip)

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
            _add(info[4][0])
    except OSError:
        pass

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        _add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass

    return ordered


def resolve_bind_host() -> str:
    raw = os.environ.get("CNEXUS_BIND_HOST")
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    if auto_network_enabled():
        return "0.0.0.0"
    return "127.0.0.1"


def resolve_public_url(port: int = 7864) -> str:
    explicit = _normalize_host(str(os.environ.get("CNEXUS_PUBLIC_URL", "") or ""))
    if explicit:
        return explicit
    if not auto_network_enabled():
        return ""
    ips = list_lan_ipv4()
    if ips:
        return f"http://{ips[0]}:{int(port)}"
    return ""
