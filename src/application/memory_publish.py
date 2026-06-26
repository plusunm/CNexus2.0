"""Encode local memory blocks as verified chunks for cognitive publish."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Sequence, Tuple

try:
    from protocol.ids import compute_chunk_hash
    from protocol.models import Commit, Graph, GraphMetadata, Manifest
except ImportError:
    from cnexus_protocol.ids import compute_chunk_hash
    from cnexus_protocol.models import Commit, Graph, GraphMetadata, Manifest


def encode_memory_blocks(blocks: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Serialize memory blocks to chunk payloads + hashes (bytes→hash truth)."""
    payloads: List[Dict[str, Any]] = []
    hashes: List[str] = []
    for block in blocks:
        row = dict(block or {})
        raw = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        chunk_hash = compute_chunk_hash(raw)
        payloads.append({"hash": chunk_hash, "bytes": raw})
        hashes.append(chunk_hash)
    return payloads, hashes


def build_memory_publish_objects(
    *,
    graph_id: str,
    owner: str,
    topic: str,
    chunk_hashes: Iterable[str],
    parent_ids: Sequence[str] = (),
    constitution_hash: str,
    signature: str = "memory-publish",
    message: str = "",
) -> Tuple[Graph, Commit, Manifest]:
    """Build Graph + Commit + Manifest for a memory-backed publish."""
    hashes = list(chunk_hashes)
    manifest = Manifest.from_chunk_hashes(hashes, graph_id=graph_id)
    commit = Commit.build(
        graph_id=graph_id,
        parent_ids=tuple(parent_ids),
        root_hash=manifest.root_hash,
        author=owner,
        constitution_hash=constitution_hash,
        signature=signature,
        message=message or f"memory publish ({len(hashes)} chunks)",
    )
    manifest = Manifest.from_chunk_hashes(
        manifest.chunk_hashes(),
        graph_id=graph_id,
        commit_id=commit.commit_id,
    )
    graph = Graph(
        graph_id=graph_id,
        owner=owner,
        metadata=GraphMetadata(topic=topic, tags=("memory",)),
    )
    return graph, commit, manifest
