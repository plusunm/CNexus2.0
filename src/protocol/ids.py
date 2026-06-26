"""Identity helpers — GraphID permanence, CommitID content addressing."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Iterable, Optional


_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")


def normalize_peer_id(value: str) -> str:
    peer_id = str(value or "").strip().lower()
    if not _HEX64.fullmatch(peer_id):
        raise ValueError("peer_id must be 64 hex chars (Ed25519 public key)")
    return peer_id


def normalize_graph_id(value: str) -> str:
    graph_id = str(value or "").strip().lower()
    if not _HEX32.fullmatch(graph_id):
        raise ValueError("graph_id must be 32 hex chars (permanent graph identity)")
    return graph_id


def normalize_commit_id(value: str) -> str:
    commit_id = str(value or "").strip().lower()
    if not _HEX64.fullmatch(commit_id):
        raise ValueError("commit_id must be 64 hex chars")
    return commit_id


def normalize_hash64(value: str, *, field: str = "hash") -> str:
    digest = str(value or "").strip().lower()
    if not _HEX64.fullmatch(digest):
        raise ValueError(f"{field} must be 64 hex chars")
    return digest


def new_graph_id() -> str:
    """Permanent graph identity — never changes when content commits advance."""
    return uuid.uuid4().hex


def graph_id_for_owner_topic(owner_peer_id: str, topic: str) -> str:
    """
    Deterministic GraphID for an owner + human topic slug.
    Same owner + topic → same GraphID (idempotent publish namespace).
    Different owners may use the same topic string without collision.
    """
    owner = normalize_peer_id(owner_peer_id)
    slug = str(topic or "").strip().lower()
    if not slug:
        raise ValueError("topic required for owner-scoped graph id")
    digest = hashlib.sha256(f"cnexus:graph:v1:{owner}:{slug}".encode("utf-8")).hexdigest()
    return digest[:32]


def compute_commit_id(
    *,
    graph_id: str,
    parent_ids: Iterable[str],
    root_hash: str,
    author_peer_id: str,
    constitution_hash: str,
) -> str:
    """
    CommitID = SHA256(canonical commit material).
    GraphID stays fixed; CommitID changes on every new commit.
    """
    from .serialization import canonical_json

    material = canonical_json(
        {
            "graph_id": normalize_graph_id(graph_id),
            "parent_ids": sorted(normalize_commit_id(p) for p in parent_ids),
            "root_hash": normalize_hash64(root_hash, field="root_hash"),
            "author": normalize_peer_id(author_peer_id),
            "constitution_hash": normalize_hash64(constitution_hash, field="constitution_hash"),
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def compute_chunk_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compute_root_hash(chunk_hashes: Iterable[str]) -> str:
    """
    Manifest root = SHA256(canonical sorted chunk hash list).
    Commit.root_hash references this manifest root (content-addressed, not payload).
    """
    from .serialization import canonical_json

    hashes = sorted(normalize_hash64(str(h), field="chunk_hash") for h in chunk_hashes if str(h).strip())
    material = canonical_json({"chunks": hashes, "manifest_version": 1})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def optional_graph_id(value: Optional[str]) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    return normalize_graph_id(value)
