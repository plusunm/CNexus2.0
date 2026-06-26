"""P5.0 — Manifest ↔ ChunkStore missing detection."""

from __future__ import annotations

from typing import Iterable, List, Optional, Set

try:
    from protocol.models import Manifest, MissingDiff
except ImportError:
    from cnexus_protocol.models import Manifest, MissingDiff

from ..chunk_store import ChunkStore
from ..manifest_store import ManifestStore


def diff_manifest(
    manifest: Manifest,
    chunk_store: ChunkStore,
    *,
    graph_id: str = "",
    commit_id: str = "",
) -> MissingDiff:
    """
    Compare manifest orchestration against local ChunkStore truth.
    Verification: bytes→hash for present; missing = not in store; invalid = corrupt.
    """
    missing: List[str] = []
    present: List[str] = []
    invalid: List[str] = []
    manifest_hashes: Set[str] = set()

    for chunk_hash in manifest.chunk_hashes():
        manifest_hashes.add(chunk_hash)
        if not chunk_store.has(chunk_hash):
            missing.append(chunk_hash)
        elif chunk_store.verify(chunk_hash):
            present.append(chunk_hash)
        else:
            invalid.append(chunk_hash)

    unknown: List[str] = []
    for chunk_hash in _orphan_hashes(chunk_store, manifest_hashes):
        unknown.append(chunk_hash)

    return MissingDiff(
        root_hash=manifest.root_hash,
        missing=tuple(missing),
        present=tuple(present),
        invalid=tuple(invalid),
        unknown=tuple(unknown),
        graph_id=str(graph_id or manifest.graph_id or ""),
        commit_id=str(commit_id or manifest.commit_id or ""),
    )


def diff_by_root(
    manifest_store: ManifestStore,
    chunk_store: ChunkStore,
    *,
    root_hash: str = "",
    commit_id: str = "",
) -> Optional[MissingDiff]:
    manifest = None
    if commit_id:
        manifest = manifest_store.get_by_commit(commit_id)
    if manifest is None and root_hash:
        manifest = manifest_store.get(root_hash)
    if manifest is None:
        return None
    return diff_manifest(
        manifest,
        chunk_store,
        graph_id=str(manifest.graph_id or ""),
        commit_id=str(commit_id or manifest.commit_id or ""),
    )


def diff_all_manifests(manifest_store: ManifestStore, chunk_store: ChunkStore) -> List[MissingDiff]:
    rows: List[MissingDiff] = []
    for root in manifest_store.list_roots():
        manifest = manifest_store.get(root)
        if manifest is None:
            continue
        rows.append(diff_manifest(manifest, chunk_store))
    return rows


def _orphan_hashes(chunk_store: ChunkStore, manifest_hashes: Set[str]) -> Iterable[str]:
    """Local blobs with no manifest reference (informational unknown set)."""
    if not hasattr(chunk_store, "chunks_dir"):
        return ()
    orphans: List[str] = []
    base = chunk_store.chunks_dir
    if not base.exists():
        return ()
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        digest = path.name.lower()
        if len(digest) == 64 and digest not in manifest_hashes:
            orphans.append(digest)
    return orphans
