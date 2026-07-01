"""Built-in trusted peers seeded on first run (Personal edition)."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List

# Cloud rendezvous hub (华东1 杭州 ECS) — always-on, public reachability.
_DEFAULT_HUB_PUBKEY = "4cbe1a21e9e202b128fa07395a6e06ab9ad7e2861bcdd7ce411e2f24c5b817ed"
_DEFAULT_HUB_HOST = "http://114.55.62.198:7864"

# Maintainer local device — trusted by default; reachable via LAN/DHT when online.
_DEFAULT_LOCAL_FOUNDER_PUBKEY = "d7ff9669ed23349e92490ac03cc58980fb6440382637f944077bb0b4e5e68075"

HUB_PUBKEY = os.environ.get(
    "CNEXUS_HUB_PUBKEY",
    os.environ.get("CNEXUS_FOUNDER_PUBKEY", _DEFAULT_HUB_PUBKEY),
).strip().lower()
HUB_HOST = os.environ.get(
    "CNEXUS_HUB_HOST",
    os.environ.get("CNEXUS_FOUNDER_HOST", _DEFAULT_HUB_HOST),
).strip()
LOCAL_FOUNDER_PUBKEY = os.environ.get(
    "CNEXUS_LOCAL_FOUNDER_PUBKEY",
    _DEFAULT_LOCAL_FOUNDER_PUBKEY,
).strip().lower()

# Backward-compatible aliases (hub = primary public rendezvous).
FOUNDER_PUBKEY = HUB_PUBKEY
FOUNDER_HOST_HINT = HUB_HOST

BOOTSTRAP_TRUSTED_PEERS: List[Dict[str, Any]] = [
    {
        "pubkey": HUB_PUBKEY,
        "host": HUB_HOST,
        "label": "hub",
        "bootstrap": True,
    },
    {
        "pubkey": LOCAL_FOUNDER_PUBKEY,
        "host": "",
        "label": "founder",
        "bootstrap": True,
    },
]


def bootstrap_host_for_pubkey(pubkey: str) -> str:
    """Known bootstrap host for a pubkey, or empty string."""
    needle = str(pubkey or "").strip().lower()
    if not needle:
        return ""
    for row in BOOTSTRAP_TRUSTED_PEERS:
        if str(row.get("pubkey") or "").strip().lower() == needle:
            return str(row.get("host") or "").strip()
    return ""


def bootstrap_peers_public() -> List[Dict[str, Any]]:
    """Sanitized bootstrap peer list for API / frontend."""
    rows: List[Dict[str, Any]] = []
    for row in BOOTSTRAP_TRUSTED_PEERS:
        pubkey = str(row.get("pubkey") or "").strip().lower()
        if not pubkey:
            continue
        rows.append(
            {
                "pubkey": pubkey,
                "host": str(row.get("host") or "").strip(),
                "label": str(row.get("label") or ""),
            }
        )
    return rows


def ensure_bootstrap_peers(peer_registry, local_pubkey: str = "") -> List[str]:
    """Ensure built-in trusted peers exist. Returns pubkeys newly (re)added."""
    if peer_registry is None:
        return []
    local = str(local_pubkey or "").strip().lower()
    added: List[str] = []
    for row in BOOTSTRAP_TRUSTED_PEERS:
        pubkey = str(row.get("pubkey") or "").strip().lower()
        if not pubkey or pubkey == local:
            continue
        if peer_registry.get_peer(pubkey):
            continue
        host = str(row.get("host") or "").strip()
        peer_registry.save_peer(pubkey, host, status="trusted")
        if row.get("label") or row.get("bootstrap"):
            peer_registry.update_peer(
                pubkey,
                label=row.get("label"),
                bootstrap=bool(row.get("bootstrap")),
            )
        added.append(pubkey)
    return added


def schedule_bootstrap_connect(
    peer_registry,
    connect_fn: Callable[[str, str], Any],
    *,
    delay_s: float = 8.0,
) -> None:
    """Background: try DHT/LAN connect to seeded peers (best-effort)."""
    if peer_registry is None:
        return

    targets: List[tuple[str, str]] = []
    for row in BOOTSTRAP_TRUSTED_PEERS:
        pubkey = str(row.get("pubkey") or "").strip().lower()
        if not pubkey:
            continue
        meta = peer_registry.get_peer(pubkey) or {}
        if str(meta.get("status") or "") not in ("trusted", "online", "discovered"):
            continue
        host = str(row.get("host") or meta.get("host") or "").strip()
        targets.append((pubkey, host))

    if not targets:
        return

    def _worker():
        time.sleep(max(0.0, float(delay_s)))
        for pubkey, host in targets:
            try:
                connect_fn(pubkey, host)
            except Exception:
                pass
            time.sleep(1.5)

    threading.Thread(target=_worker, name="cnexus-founder-connect", daemon=True).start()
