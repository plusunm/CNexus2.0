"""P5.1 — Suggested repair sources (deterministic ranking, not trust scoring)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def suggest_repair_sources(
    *,
    connected_host: str = "",
    connected_peer_id: str = "",
    peer_registry=None,
    descriptor_sources: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Deterministic source ordering for repair observability.
    Suggested only — no execution, no trust score (P5+ reserved).
    """
    suggestions: List[Dict[str, Any]] = []
    seen_hosts: set[str] = set()
    rank = 1

    host = str(connected_host or "").strip().rstrip("/")
    if host:
        if not host.startswith(("http://", "https://")):
            host = "http://" + host
        seen_hosts.add(host.lower())
        suggestions.append(
            {
                "rank": rank,
                "host": host,
                "peer_id": str(connected_peer_id or "")[:64],
                "reason": "connected_peer",
                "explain": "Peer that completed handshake on this connect session",
            }
        )
        rank += 1

    for src in descriptor_sources or []:
        candidate = str(src or "").strip()
        if not candidate or candidate.lower() in seen_hosts:
            continue
        if not candidate.startswith(("http://", "https://")):
            if len(candidate) == 64:
                continue
            candidate = "http://" + candidate
        seen_hosts.add(candidate.lower())
        suggestions.append(
            {
                "rank": rank,
                "host": candidate,
                "peer_id": "",
                "reason": "descriptor_provenance",
                "explain": "Previously recorded successful chunk source from ChunkDescriptor",
            }
        )
        rank += 1

    if peer_registry is not None:
        try:
            peers = peer_registry.get_all_peers()
        except Exception:
            peers = {}
        for pubkey, meta in sorted(peers.items()):
            if not isinstance(meta, dict):
                continue
            reg_host = str(meta.get("host") or "").strip().rstrip("/")
            if not reg_host:
                continue
            if not reg_host.startswith(("http://", "https://")):
                reg_host = "http://" + reg_host
            if reg_host.lower() in seen_hosts:
                continue
            status = str(meta.get("status") or "")
            if status not in ("trusted", "online", "discovered"):
                continue
            seen_hosts.add(reg_host.lower())
            suggestions.append(
                {
                    "rank": rank,
                    "host": reg_host,
                    "peer_id": str(pubkey)[:64],
                    "reason": "trusted_registry_peer",
                    "explain": f"Peer registry entry (status={status})",
                }
            )
            rank += 1

    return suggestions
