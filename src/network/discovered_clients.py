"""Merge registry, DHT, and LAN scan into a unified CNexus client discovery list."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence


def _short_pubkey(pubkey: str) -> str:
    pk = str(pubkey or "").strip()
    if len(pk) <= 16:
        return pk
    return f"{pk[:8]}…{pk[-6:]}"


def merge_discovered_clients(
    *,
    local_pubkey: str = "",
    registry_peers: Optional[Mapping[str, Mapping[str, Any]]] = None,
    dht_nodes: Optional[Sequence[Mapping[str, Any]]] = None,
    lan_rows: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Union of known CNexus peers — registry + DHT buckets + optional LAN scan."""
    local = str(local_pubkey or "").strip().lower()
    merged: Dict[str, MutableMapping[str, Any]] = {}

    def upsert(pubkey: str, **fields: Any) -> None:
        pk = str(pubkey or "").strip()
        if not pk or pk.lower() == local:
            return
        row: MutableMapping[str, Any] = merged.get(pk) or {
            "pubkey": pk,
            "pubkey_short": _short_pubkey(pk),
            "sources": [],
            "status": "discovered",
        }
        sources = list(row.get("sources") or [])
        for source in fields.pop("sources", []) or []:
            src = str(source or "").strip()
            if src and src not in sources:
                sources.append(src)
        row["sources"] = sources

        for key, value in fields.items():
            if value is None:
                continue
            if key == "last_seen":
                prev = float(row.get("last_seen") or 0)
                row[key] = max(prev, float(value))
            elif key == "host" and value:
                row[key] = str(value).strip()
            elif key == "status" and value:
                row[key] = str(value).strip()
            elif key not in row or not row.get(key):
                row[key] = value

        merged[pk] = row

    for pubkey, meta in dict(registry_peers or {}).items():
        meta = dict(meta or {})
        upsert(
            pubkey,
            host=meta.get("host"),
            status=str(meta.get("status") or "discovered"),
            last_seen=meta.get("last_seen"),
            sources=["registry"],
        )

    for node in dht_nodes or []:
        node = dict(node or {})
        upsert(
            str(node.get("pubkey") or ""),
            host=node.get("host"),
            last_seen=node.get("last_seen"),
            sources=["dht"],
        )

    for lan in lan_rows or []:
        lan = dict(lan or {})
        upsert(
            str(lan.get("pubkey") or ""),
            host=lan.get("host") or lan.get("url"),
            last_seen=time.time(),
            sources=["lan"],
        )

    rows: List[Dict[str, Any]] = []
    for row in merged.values():
        status = str(row.get("status") or "discovered")
        trusted = status in ("trusted", "online")
        out = dict(row)
        out["trusted"] = trusted
        out["status"] = status
        if not out.get("host"):
            out["host"] = ""
        rows.append(out)

    rows.sort(
        key=lambda item: (
            0 if item.get("trusted") else 1,
            0 if "lan" in (item.get("sources") or []) else 1,
            -(float(item.get("last_seen") or 0)),
            str(item.get("pubkey") or ""),
        )
    )
    return rows
