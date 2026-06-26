"""P0 frozen object model — Peer, Graph, Commit, Chunk, CatalogEntry, Session."""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterable, List, Mapping, Optional, Tuple

from .constants import (
    ALLOWED_CHUNK_ENCODINGS,
    CATALOG_ENTRY_OBJECT_VERSION,
    CHUNK_DESCRIPTOR_OBJECT_VERSION,
    CHUNK_ENCODING_RAW,
    CHUNK_OBJECT_VERSION,
    COMMIT_OBJECT_VERSION,
    EXECUTION_MODE_MANUAL,
    EXECUTION_POLICY_OBJECT_VERSION,
    GRAPH_OBJECT_VERSION,
    MANIFEST_OBJECT_VERSION,
    MISSING_DIFF_OBJECT_VERSION,
    PEER_OBJECT_VERSION,
    PUBLISH_TXN_OBJECT_VERSION,
    REPAIR_PLAN_OBJECT_VERSION,
    REPAIR_STRATEGY_PULL_VERIFY_STORE,
    SESSION_OBJECT_VERSION,
)
from .ids import (
    compute_commit_id,
    compute_chunk_hash,
    normalize_commit_id,
    normalize_graph_id,
    normalize_hash64,
    normalize_peer_id,
)
from .serialization import from_bytes, to_bytes


class ProtocolObject:
    """Base for wire-stable protocol objects."""

    OBJECT_TYPE: ClassVar[str] = "object"
    SCHEMA_VERSION: ClassVar[int] = 1

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_bytes(self) -> bytes:
        payload = self.to_dict()
        payload.setdefault("object_type", self.OBJECT_TYPE)
        payload.setdefault("schema_version", self.SCHEMA_VERSION)
        return to_bytes(payload)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProtocolObject":
        raise NotImplementedError

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ProtocolObject":
        return cls.from_dict(from_bytes(raw))


@dataclass(frozen=True)
class Peer(ProtocolObject):
    """
    Device-layer identity advertisement.
    PeerID is Ed25519 pubkey hex; capability is a feature bitmap.
    """

    OBJECT_TYPE: ClassVar[str] = "peer"
    SCHEMA_VERSION: ClassVar[int] = PEER_OBJECT_VERSION

    peer_id: str
    capability: int
    protocol_version: str
    crypto_suite: str = "ed25519"
    device_info: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "peer_id": self.peer_id,
            "capability": int(self.capability),
            "protocol_version": self.protocol_version,
            "crypto_suite": self.crypto_suite,
            "device_info": list(self.device_info),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Peer":
        return cls(
            peer_id=normalize_peer_id(str(data.get("peer_id") or "")),
            capability=int(data.get("capability") or 0),
            protocol_version=str(data.get("protocol_version") or ""),
            crypto_suite=str(data.get("crypto_suite") or "ed25519"),
            device_info=tuple(str(x) for x in (data.get("device_info") or [])),
        )


@dataclass(frozen=True)
class Session(ProtocolObject):
    """Session-layer binding after Device handshake (encrypted channel metadata)."""

    OBJECT_TYPE: ClassVar[str] = "session"
    SCHEMA_VERSION: ClassVar[int] = SESSION_OBJECT_VERSION

    session_id: str
    peer_id: str
    remote_peer_id: str
    established_at: float
    crypto_suite: str = "ed25519"
    expires_at: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        row = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "session_id": self.session_id,
            "peer_id": self.peer_id,
            "remote_peer_id": self.remote_peer_id,
            "established_at": float(self.established_at),
            "crypto_suite": self.crypto_suite,
        }
        if self.expires_at is not None:
            row["expires_at"] = float(self.expires_at)
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Session":
        expires = data.get("expires_at")
        return cls(
            session_id=str(data.get("session_id") or ""),
            peer_id=normalize_peer_id(str(data.get("peer_id") or "")),
            remote_peer_id=normalize_peer_id(str(data.get("remote_peer_id") or "")),
            established_at=float(data.get("established_at") or time.time()),
            crypto_suite=str(data.get("crypto_suite") or "ed25519"),
            expires_at=float(expires) if expires is not None else None,
        )


@dataclass(frozen=True)
class GraphMetadata:
    topic: str = ""
    description: str = ""
    constitution_hash: str = ""
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "description": self.description,
            "constitution_hash": self.constitution_hash,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GraphMetadata":
        const = str(data.get("constitution_hash") or "")
        return cls(
            topic=str(data.get("topic") or ""),
            description=str(data.get("description") or ""),
            constitution_hash=normalize_hash64(const, field="constitution_hash") if const else "",
            tags=tuple(str(x) for x in (data.get("tags") or [])),
        )


@dataclass(frozen=True)
class Graph(ProtocolObject):
    """
    Permanent cognitive container.
    GraphID never changes; commits advance via Commit objects.
    Owner (PeerID) establishes namespace / provenance.
    """

    OBJECT_TYPE: ClassVar[str] = "graph"
    SCHEMA_VERSION: ClassVar[int] = GRAPH_OBJECT_VERSION

    graph_id: str
    owner: str
    metadata: GraphMetadata = field(default_factory=GraphMetadata)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "graph_id": self.graph_id,
            "owner": self.owner,
            "metadata": self.metadata.to_dict(),
            "created_at": float(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Graph":
        return cls(
            graph_id=normalize_graph_id(str(data.get("graph_id") or "")),
            owner=normalize_peer_id(str(data.get("owner") or "")),
            metadata=GraphMetadata.from_dict(data.get("metadata") or {}),
            created_at=float(data.get("created_at") or time.time()),
        )


@dataclass(frozen=True)
class Commit(ProtocolObject):
    """
    Version node in the commit DAG (Git-like, graph-native).
    Merge commits carry multiple parent_ids.
    """

    OBJECT_TYPE: ClassVar[str] = "commit"
    SCHEMA_VERSION: ClassVar[int] = COMMIT_OBJECT_VERSION

    commit_id: str
    graph_id: str
    parent_ids: Tuple[str, ...]
    root_hash: str
    author: str
    constitution_hash: str
    signature: str
    timestamp: float = field(default_factory=time.time)
    message: str = ""

    @classmethod
    def build(
        cls,
        *,
        graph_id: str,
        parent_ids: Tuple[str, ...],
        root_hash: str,
        author: str,
        constitution_hash: str,
        signature: str,
        timestamp: Optional[float] = None,
        message: str = "",
    ) -> "Commit":
        commit_id = compute_commit_id(
            graph_id=graph_id,
            parent_ids=parent_ids,
            root_hash=root_hash,
            author_peer_id=author,
            constitution_hash=constitution_hash,
        )
        return cls(
            commit_id=commit_id,
            graph_id=normalize_graph_id(graph_id),
            parent_ids=tuple(normalize_commit_id(p) for p in parent_ids),
            root_hash=normalize_hash64(root_hash, field="root_hash"),
            author=normalize_peer_id(author),
            constitution_hash=normalize_hash64(constitution_hash, field="constitution_hash"),
            signature=str(signature or ""),
            timestamp=float(timestamp if timestamp is not None else time.time()),
            message=str(message or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "commit_id": self.commit_id,
            "graph_id": self.graph_id,
            "parent_ids": list(self.parent_ids),
            "root_hash": self.root_hash,
            "author": self.author,
            "constitution_hash": self.constitution_hash,
            "signature": self.signature,
            "timestamp": float(self.timestamp),
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Commit":
        parents = tuple(normalize_commit_id(str(p)) for p in (data.get("parent_ids") or []))
        commit_id = str(data.get("commit_id") or "")
        graph_id = normalize_graph_id(str(data.get("graph_id") or ""))
        root_hash = normalize_hash64(str(data.get("root_hash") or ""), field="root_hash")
        author = normalize_peer_id(str(data.get("author") or ""))
        constitution_hash = normalize_hash64(
            str(data.get("constitution_hash") or ""),
            field="constitution_hash",
        )
        if not commit_id:
            commit_id = compute_commit_id(
                graph_id=graph_id,
                parent_ids=parents,
                root_hash=root_hash,
                author_peer_id=author,
                constitution_hash=constitution_hash,
            )
        else:
            commit_id = normalize_commit_id(commit_id)
        return cls(
            commit_id=commit_id,
            graph_id=graph_id,
            parent_ids=parents,
            root_hash=root_hash,
            author=author,
            constitution_hash=constitution_hash,
            signature=str(data.get("signature") or ""),
            timestamp=float(data.get("timestamp") or time.time()),
            message=str(data.get("message") or ""),
        )


@dataclass(frozen=True)
class Chunk(ProtocolObject):
    """Content-addressed storage block (BitTorrent-like piece descriptor)."""

    OBJECT_TYPE: ClassVar[str] = "chunk"
    SCHEMA_VERSION: ClassVar[int] = CHUNK_OBJECT_VERSION

    chunk_hash: str
    offset: int
    length: int
    graph_id: Optional[str] = None
    commit_id: Optional[str] = None

    @classmethod
    def from_content(
        cls,
        content: bytes,
        *,
        offset: int = 0,
        graph_id: Optional[str] = None,
        commit_id: Optional[str] = None,
    ) -> "Chunk":
        return cls(
            chunk_hash=compute_chunk_hash(content),
            offset=int(offset),
            length=len(content),
            graph_id=normalize_graph_id(graph_id) if graph_id else None,
            commit_id=normalize_commit_id(commit_id) if commit_id else None,
        )

    def to_dict(self) -> dict[str, Any]:
        row = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "chunk_hash": self.chunk_hash,
            "offset": int(self.offset),
            "length": int(self.length),
        }
        if self.graph_id:
            row["graph_id"] = self.graph_id
        if self.commit_id:
            row["commit_id"] = self.commit_id
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Chunk":
        gid = data.get("graph_id")
        cid = data.get("commit_id")
        return cls(
            chunk_hash=normalize_hash64(str(data.get("chunk_hash") or ""), field="chunk_hash"),
            offset=int(data.get("offset") or 0),
            length=int(data.get("length") or 0),
            graph_id=normalize_graph_id(str(gid)) if gid else None,
            commit_id=normalize_commit_id(str(cid)) if cid else None,
        )


@dataclass(frozen=True)
class ChunkDescriptor(ProtocolObject):
    """
    P4.5 Chunk Consistency Contract — network identity for a content-addressed chunk.

    NOT part of Manifest. Chunk is owned by Hash, not Manifest or Peer.
    Immutable + verifiable + transferable + reproducible semantics.
    """

    OBJECT_TYPE: ClassVar[str] = "chunk_descriptor"
    SCHEMA_VERSION: ClassVar[int] = CHUNK_DESCRIPTOR_OBJECT_VERSION

    chunk_hash: str
    size: int
    encoding: str = CHUNK_ENCODING_RAW
    compression: Optional[str] = None
    created_by: str = ""
    verified_by: Tuple[str, ...] = ()
    sources: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "hash": self.chunk_hash,
            "size": int(self.size),
            "encoding": self.encoding,
        }
        if self.compression:
            row["compression"] = self.compression
        if self.created_by:
            row["created_by"] = self.created_by
        if self.verified_by:
            row["verified_by"] = list(self.verified_by)
        if self.sources:
            row["peers"] = list(self.sources)
            row["sources"] = list(self.sources)
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ChunkDescriptor":
        encoding = str(data.get("encoding") or CHUNK_ENCODING_RAW)
        if encoding not in ALLOWED_CHUNK_ENCODINGS:
            raise ValueError(f"unsupported chunk encoding: {encoding}")
        chunk_hash = normalize_hash64(
            str(data.get("hash") or data.get("chunk_hash") or ""),
            field="chunk_hash",
        )
        verified = tuple(str(x) for x in (data.get("verified_by") or []))
        sources = tuple(str(x) for x in (data.get("sources") or data.get("peers") or []))
        created_raw = str(data.get("created_by") or "")
        return cls(
            chunk_hash=chunk_hash,
            size=int(data.get("size") or 0),
            encoding=encoding,
            compression=str(data.get("compression")) if data.get("compression") else None,
            created_by=normalize_peer_id(created_raw) if created_raw else "",
            verified_by=verified,
            sources=sources,
        )

    @classmethod
    def for_content(
        cls,
        content: bytes,
        chunk_hash: str,
        *,
        created_by: str = "",
        encoding: str = CHUNK_ENCODING_RAW,
    ) -> "ChunkDescriptor":
        if encoding not in ALLOWED_CHUNK_ENCODINGS:
            raise ValueError(f"unsupported chunk encoding: {encoding}")
        return cls(
            chunk_hash=normalize_hash64(chunk_hash, field="chunk_hash"),
            size=len(content),
            encoding=encoding,
            created_by=normalize_peer_id(created_by) if created_by else "",
        )


@dataclass(frozen=True)
class MissingDiff(ProtocolObject):
    """
    P5.0 — Manifest ↔ ChunkStore integrity diff.
    Entry point for repair: missing detection, not replication.
    """

    OBJECT_TYPE: ClassVar[str] = "missing_diff"
    SCHEMA_VERSION: ClassVar[int] = MISSING_DIFF_OBJECT_VERSION

    root_hash: str
    missing: Tuple[str, ...] = ()
    present: Tuple[str, ...] = ()
    invalid: Tuple[str, ...] = ()
    unknown: Tuple[str, ...] = ()
    graph_id: str = ""
    commit_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "root_hash": self.root_hash,
            "missing": list(self.missing),
            "present": list(self.present),
            "invalid": list(self.invalid),
            "unknown": list(self.unknown),
        }
        if self.graph_id:
            row["graph_id"] = self.graph_id
        if self.commit_id:
            row["commit_id"] = self.commit_id
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MissingDiff":
        return cls(
            root_hash=normalize_hash64(str(data.get("root_hash") or ""), field="root_hash"),
            missing=tuple(normalize_hash64(str(h), field="chunk_hash") for h in (data.get("missing") or [])),
            present=tuple(normalize_hash64(str(h), field="chunk_hash") for h in (data.get("present") or [])),
            invalid=tuple(normalize_hash64(str(h), field="chunk_hash") for h in (data.get("invalid") or [])),
            unknown=tuple(normalize_hash64(str(h), field="chunk_hash") for h in (data.get("unknown") or [])),
            graph_id=normalize_graph_id(str(data.get("graph_id") or "")) if data.get("graph_id") else "",
            commit_id=normalize_commit_id(str(data.get("commit_id") or "")) if data.get("commit_id") else "",
        )


@dataclass(frozen=True)
class RepairPlan(ProtocolObject):
    """
    P5.1 — Repair intent (not execution).
    Chunk is repaired, not synced. Triggered by diff/plan only.
    """

    OBJECT_TYPE: ClassVar[str] = "repair_plan"
    SCHEMA_VERSION: ClassVar[int] = REPAIR_PLAN_OBJECT_VERSION

    chunk_hash: str
    priority: float
    sources: Tuple[str, ...]
    strategy: str = REPAIR_STRATEGY_PULL_VERIFY_STORE
    root_hash: str = ""
    graph_id: str = ""
    commit_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "hash": self.chunk_hash,
            "chunk_hash": self.chunk_hash,
            "priority": float(self.priority),
            "sources": list(self.sources),
            "strategy": self.strategy,
        }
        if self.root_hash:
            row["root_hash"] = self.root_hash
        if self.graph_id:
            row["graph_id"] = self.graph_id
        if self.commit_id:
            row["commit_id"] = self.commit_id
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RepairPlan":
        return cls(
            chunk_hash=normalize_hash64(str(data.get("hash") or data.get("chunk_hash") or ""), field="chunk_hash"),
            priority=float(data.get("priority") or 0),
            sources=tuple(str(s) for s in (data.get("sources") or [])),
            strategy=str(data.get("strategy") or REPAIR_STRATEGY_PULL_VERIFY_STORE),
            root_hash=normalize_hash64(str(data.get("root_hash") or ""), field="root_hash") if data.get("root_hash") else "",
            graph_id=normalize_graph_id(str(data.get("graph_id") or "")) if data.get("graph_id") else "",
            commit_id=normalize_commit_id(str(data.get("commit_id") or "")) if data.get("commit_id") else "",
        )


@dataclass(frozen=True)
class ExecutionPolicy(ProtocolObject):
    """
    P5.3 — Execution boundary. Who may run repair and under what evidence.
    Repair is permitted, not inferred. No autonomous execution.
    """

    OBJECT_TYPE: ClassVar[str] = "execution_policy"
    SCHEMA_VERSION: ClassVar[int] = EXECUTION_POLICY_OBJECT_VERSION

    mode: str = EXECUTION_MODE_MANUAL
    allowed_sources: Tuple[str, ...] = (
        "connected_peer",
        "trusted_registry_peer",
        "descriptor_provenance",
    )
    require_probe: bool = True
    max_concurrency: int = 2
    require_user_confirm: bool = True
    max_plans: int = 32

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "mode": self.mode,
            "allowed_sources": list(self.allowed_sources),
            "require_probe": bool(self.require_probe),
            "max_concurrency": int(self.max_concurrency),
            "require_user_confirm": bool(self.require_user_confirm),
            "max_plans": int(self.max_plans),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionPolicy":
        mode = str(data.get("mode") or EXECUTION_MODE_MANUAL)
        if mode != EXECUTION_MODE_MANUAL:
            raise ValueError(f"unsupported execution mode: {mode}")
        allowed = tuple(str(x) for x in (data.get("allowed_sources") or cls().allowed_sources))
        return cls(
            mode=mode,
            allowed_sources=allowed,
            require_probe=bool(data.get("require_probe", True)),
            max_concurrency=int(data.get("max_concurrency") or 2),
            require_user_confirm=bool(data.get("require_user_confirm", True)),
            max_plans=int(data.get("max_plans") or 32),
        )

    @classmethod
    def default(cls) -> "ExecutionPolicy":
        return cls()


@dataclass(frozen=True)
class Manifest(ProtocolObject):
    """
    P3.5 content manifest — Commit references root_hash, not payload.
    Chunks may be hash-only refs (offset/length 0) until P4 Chunk Store.
    """

    OBJECT_TYPE: ClassVar[str] = "manifest"
    SCHEMA_VERSION: ClassVar[int] = MANIFEST_OBJECT_VERSION

    root_hash: str
    chunks: Tuple[Chunk, ...] = ()
    graph_id: Optional[str] = None
    commit_id: Optional[str] = None

    @classmethod
    def from_chunk_hashes(
        cls,
        chunk_hashes: Iterable[str],
        *,
        graph_id: Optional[str] = None,
        commit_id: Optional[str] = None,
    ) -> "Manifest":
        from .ids import compute_root_hash

        hashes = sorted(normalize_hash64(str(h), field="chunk_hash") for h in chunk_hashes if str(h).strip())
        root = compute_root_hash(hashes)
        gid = normalize_graph_id(graph_id) if graph_id else None
        cid = normalize_commit_id(commit_id) if commit_id else None
        chunks = tuple(Chunk(chunk_hash=h, offset=0, length=0, graph_id=gid, commit_id=cid) for h in hashes)
        return cls(root_hash=root, chunks=chunks, graph_id=gid, commit_id=cid)

    def chunk_hashes(self) -> Tuple[str, ...]:
        return tuple(c.chunk_hash for c in self.chunks)

    def verify_root(self) -> bool:
        from .ids import compute_root_hash

        return self.root_hash == compute_root_hash(self.chunk_hashes())

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "root_hash": self.root_hash,
            "chunks": list(self.chunk_hashes()),
        }
        if self.graph_id:
            row["graph_id"] = self.graph_id
        if self.commit_id:
            row["commit_id"] = self.commit_id
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Manifest":
        from .ids import compute_root_hash

        gid = data.get("graph_id")
        cid = data.get("commit_id")
        raw_chunks = data.get("chunks") or []
        parsed: List[Chunk] = []
        for item in raw_chunks:
            if isinstance(item, str):
                parsed.append(
                    Chunk(
                        chunk_hash=normalize_hash64(item, field="chunk_hash"),
                        offset=0,
                        length=0,
                        graph_id=normalize_graph_id(str(gid)) if gid else None,
                        commit_id=normalize_commit_id(str(cid)) if cid else None,
                    )
                )
            elif isinstance(item, Mapping):
                parsed.append(Chunk.from_dict(item))
        root_raw = str(data.get("root_hash") or "")
        if root_raw:
            root = normalize_hash64(root_raw, field="root_hash")
        else:
            root = compute_root_hash(c.chunk_hash for c in parsed)
        return cls(
            root_hash=root,
            chunks=tuple(parsed),
            graph_id=normalize_graph_id(str(gid)) if gid else None,
            commit_id=normalize_commit_id(str(cid)) if cid else None,
        )


@dataclass(frozen=True)
class PublishTxn(ProtocolObject):
    """
    Atomic publish journal — CommitStore → Catalog with crash recovery.
    Phases: pending_commit → pending_catalog → committed.
    """

    OBJECT_TYPE: ClassVar[str] = "publish_txn"
    SCHEMA_VERSION: ClassVar[int] = PUBLISH_TXN_OBJECT_VERSION

    txn_id: str
    phase: str
    graph: dict[str, Any]
    commit: dict[str, Any]
    manifest: dict[str, Any]
    size: int = 0
    created_at: float = field(default_factory=time.time)

    PHASE_PENDING_COMMIT: ClassVar[str] = "pending_commit"
    PHASE_PENDING_CATALOG: ClassVar[str] = "pending_catalog"
    PHASE_COMMITTED: ClassVar[str] = "committed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "txn_id": self.txn_id,
            "phase": self.phase,
            "graph": dict(self.graph),
            "commit": dict(self.commit),
            "manifest": dict(self.manifest),
            "size": int(self.size),
            "created_at": float(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PublishTxn":
        return cls(
            txn_id=str(data.get("txn_id") or ""),
            phase=str(data.get("phase") or cls.PHASE_PENDING_COMMIT),
            graph=dict(data.get("graph") or {}),
            commit=dict(data.get("commit") or {}),
            manifest=dict(data.get("manifest") or {}),
            size=int(data.get("size") or 0),
            created_at=float(data.get("created_at") or time.time()),
        )


@dataclass(frozen=True)
class BloomSummary(ProtocolObject):
    """Compact Bloom digest for skip-before-download (Catalog Layer)."""

    OBJECT_TYPE: ClassVar[str] = "bloom_summary"
    SCHEMA_VERSION: ClassVar[int] = 1

    generation: int
    entry_count: int
    bit_count: int
    hash_count: int
    digest: str
    namespace: str = "catalog/system"

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "generation": int(self.generation),
            "entry_count": int(self.entry_count),
            "bit_count": int(self.bit_count),
            "hash_count": int(self.hash_count),
            "digest": self.digest,
            "namespace": self.namespace,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BloomSummary":
        return cls(
            generation=int(data.get("generation") or 0),
            entry_count=int(data.get("entry_count") or 0),
            bit_count=int(data.get("bit_count") or 0),
            hash_count=int(data.get("hash_count") or 0),
            digest=str(data.get("digest") or ""),
            namespace=str(data.get("namespace") or "catalog/system"),
        )


@dataclass(frozen=True)
class CatalogHead(ProtocolObject):
    """P3-ready graph HEAD — maps to Commit DAG entry point."""

    OBJECT_TYPE: ClassVar[str] = "catalog_head"
    SCHEMA_VERSION: ClassVar[int] = 1

    graph_id: str
    head_commit: str
    head_generation: int
    root_hash: str
    catalog_generation: int = 0
    owner: str = ""
    topic: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "graph_id": self.graph_id,
            "head_commit": self.head_commit,
            "latest_commit_id": self.head_commit,
            "head_generation": int(self.head_generation),
            "root_hash": self.root_hash,
            "generation": int(self.catalog_generation),
            "owner": self.owner,
            "topic": self.topic,
        }

    @classmethod
    def from_entry(cls, entry: "CatalogEntry", *, catalog_generation: int = 0) -> "CatalogHead":
        return cls(
            graph_id=entry.graph_id,
            head_commit=entry.latest_commit_id,
            head_generation=int(entry.head_generation),
            root_hash=entry.root_hash,
            catalog_generation=int(catalog_generation),
            owner=entry.owner,
            topic=entry.topic,
        )


@dataclass(frozen=True)
class CatalogEntry(ProtocolObject):
    """
    Catalog-layer index row — NOT handshake payload.
    Bloom filter summarizes chunk presence; index exchange stays small.
    """

    OBJECT_TYPE: ClassVar[str] = "catalog_entry"
    SCHEMA_VERSION: ClassVar[int] = CATALOG_ENTRY_OBJECT_VERSION

    graph_id: str
    latest_commit_id: str
    root_hash: str
    size: int
    bloom_filter: bytes
    updated_at: float = field(default_factory=time.time)
    owner: str = ""
    topic: str = ""
    head_generation: int = 1
    chunks: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        row = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "graph_id": self.graph_id,
            "latest_commit_id": self.latest_commit_id,
            "head_commit": self.latest_commit_id,
            "root_hash": self.root_hash,
            "size": int(self.size),
            "bloom_filter": base64.b64encode(self.bloom_filter).decode("ascii"),
            "updated_at": float(self.updated_at),
            "owner": self.owner,
            "topic": self.topic,
            "head_generation": int(self.head_generation),
        }
        if self.chunks:
            row["chunks"] = list(self.chunks)
        return row

    def to_head(self, *, catalog_generation: int = 0) -> CatalogHead:
        return CatalogHead.from_entry(self, catalog_generation=catalog_generation)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CatalogEntry":
        bloom_b64 = str(data.get("bloom_filter") or "")
        bloom = base64.b64decode(bloom_b64.encode("ascii")) if bloom_b64 else b""
        owner_raw = str(data.get("owner") or "")
        chunks_raw = data.get("chunks") or []
        chunks = tuple(
            normalize_hash64(str(h), field="chunk_hash")
            for h in chunks_raw
            if str(h).strip()
        )
        return cls(
            graph_id=normalize_graph_id(str(data.get("graph_id") or "")),
            latest_commit_id=normalize_commit_id(str(data.get("latest_commit_id") or "")),
            root_hash=normalize_hash64(str(data.get("root_hash") or ""), field="root_hash"),
            size=int(data.get("size") or 0),
            bloom_filter=bloom,
            updated_at=float(data.get("updated_at") or time.time()),
            owner=normalize_peer_id(owner_raw) if owner_raw else "",
            topic=str(data.get("topic") or ""),
            head_generation=int(data.get("head_generation") or 1),
            chunks=chunks,
        )


@dataclass(frozen=True)
class HandshakeHello(ProtocolObject):
    """
    Device + Session handshake preamble — cognition-free.
    Allowed: identity, capability, protocol version, crypto suite.
    """

    OBJECT_TYPE: ClassVar[str] = "handshake_hello"
    SCHEMA_VERSION: ClassVar[int] = 1

    peer_id: str
    protocol_version: str
    capability: int
    crypto_suite: str = "ed25519"
    host: str = ""

    def to_dict(self) -> dict[str, Any]:
        row = {
            "object_type": self.OBJECT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
            "action": "HELLO",
            "peer_id": self.peer_id,
            "protocol_version": self.protocol_version,
            "capability": int(self.capability),
            "crypto_suite": self.crypto_suite,
        }
        if self.host:
            row["host"] = self.host
        return row

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HandshakeHello":
        peer_id = str(data.get("peer_id") or data.get("peer_pubkey") or data.get("pubkey") or "")
        return cls(
            peer_id=normalize_peer_id(peer_id),
            protocol_version=str(data.get("protocol_version") or ""),
            capability=int(data.get("capability") or 0),
            crypto_suite=str(data.get("crypto_suite") or "ed25519"),
            host=str(data.get("host") or data.get("peer_host") or ""),
        )
