"""Memory origin scope — local / trusted peers / network-wide."""

from __future__ import annotations

from typing import FrozenSet, Iterable, Set

MEMORY_SCOPES = frozenset({"local", "trusted", "network"})


def normalize_memory_scope(raw: object) -> str:
    value = str(raw or "local").strip().lower()
    if value in ("group", "trusted_group", "mesh", "peers"):
        return "trusted"
    if value in ("global", "wide", "dht"):
        return "network"
    return value if value in MEMORY_SCOPES else "local"


def origin_matches_scope(
    source_peer: str,
    scope: str,
    trusted: Iterable[str] | FrozenSet[str],
) -> bool:
    """Match federated search semantics: local = native only, trusted = trusted peers, network = all."""
    scope = normalize_memory_scope(scope)
    peer = str(source_peer or "").strip()
    trusted_set: Set[str] = set(trusted)
    if scope == "network":
        return True
    if scope == "trusted":
        return bool(peer) and peer in trusted_set
    return not peer
