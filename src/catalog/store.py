"""Local Catalog store — generation, HEAD, namespace-ready index."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

try:
    from protocol.models import BloomSummary, CatalogEntry, CatalogHead
except ImportError:
    from cnexus_protocol.models import BloomSummary, CatalogEntry, CatalogHead

from .bloom_builder import build_bloom, compute_bloom_params, DEFAULT_EXPECTED_ENTRIES, DEFAULT_TARGET_FPR
from .interest import CatalogInterest, filter_entries_by_interest
from .namespace import filter_entries_by_namespace, normalize_namespace


class CatalogStore:
    """Persistent graph catalog with global generation and per-graph head_generation."""

    def __init__(self, storage_path: str | Path = "data/catalog.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._generation = 0
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._chunk_hashes: Dict[str, List[str]] = {}
        self._head_generations: Dict[str, int] = {}
        self._peer_state: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return
            self._generation = int(data.get("generation") or 0)
            self._entries = dict(data.get("entries") or {})
            self._chunk_hashes = dict(data.get("chunk_hashes") or {})
            self._head_generations = dict(data.get("head_generations") or {})
            self._peer_state = dict(data.get("peer_state") or {})
        except Exception:
            self._generation = 0
            self._entries = {}
            self._chunk_hashes = {}
            self._head_generations = {}
            self._peer_state = {}

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "generation": self._generation,
                    "entries": self._entries,
                    "chunk_hashes": self._chunk_hashes,
                    "head_generations": self._head_generations,
                    "peer_state": self._peer_state,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )

    @property
    def generation(self) -> int:
        with self._lock:
            return int(self._generation)

    def get_peer_state(self, peer_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._peer_state.get(str(peer_id or "").lower()) or {})

    def set_peer_state(
        self,
        peer_id: str,
        *,
        generation: Optional[int] = None,
        summary_digest: Optional[str] = None,
        commit_cursors: Optional[Mapping[str, str]] = None,
    ) -> None:
        peer_id = str(peer_id or "").strip().lower()
        if not peer_id:
            return
        with self._lock:
            row = dict(self._peer_state.get(peer_id) or {})
            if generation is not None:
                row["generation"] = int(generation)
            if summary_digest is not None:
                row["summary_digest"] = str(summary_digest)
            if commit_cursors is not None:
                row["commit_cursors"] = dict(commit_cursors)
            self._peer_state[peer_id] = row
            self._persist()

    def upsert_entry(self, entry: CatalogEntry, *, chunk_hashes: Optional[Iterable[str]] = None) -> CatalogEntry:
        row = entry.to_dict()
        graph_id = str(row.get("graph_id") or "").strip().lower()
        if not graph_id:
            raise ValueError("graph_id required")
        row["graph_id"] = graph_id
        entry_chunks = list(entry.chunks) if entry.chunks else []
        hashes = sorted(set(str(h).lower() for h in (chunk_hashes or entry_chunks or self._chunk_hashes.get(graph_id) or [])))
        if hashes:
            row["chunks"] = hashes
        keys = [graph_id, str(row.get("latest_commit_id") or ""), str(row.get("root_hash") or ""), *hashes]
        bloom = build_bloom(keys, expected_entries=max(len(keys), DEFAULT_EXPECTED_ENTRIES))
        row["bloom_filter"] = bloom.to_base64()
        row["updated_at"] = float(row.get("updated_at") or time.time())
        with self._lock:
            prev_head = int(self._head_generations.get(graph_id) or 0)
            row["head_generation"] = prev_head + 1
            self._head_generations[graph_id] = prev_head + 1
            self._generation += 1
            self._entries[graph_id] = row
            self._chunk_hashes[graph_id] = hashes
            self._persist()
        return CatalogEntry.from_dict(row)

    def get_entry(self, graph_id: str) -> Optional[CatalogEntry]:
        gid = str(graph_id or "").strip().lower()
        row = self._entries.get(gid)
        if not row:
            return None
        return CatalogEntry.from_dict(row)

    def get_head(self, graph_id: str) -> Optional[CatalogHead]:
        entry = self.get_entry(graph_id)
        if entry is None:
            return None
        return entry.to_head(catalog_generation=self.generation)

    def list_entries(
        self,
        *,
        since_commit_cursors: Optional[Mapping[str, str]] = None,
        interest: Optional[CatalogInterest] = None,
        namespace: str = "catalog/system",
        limit: int = 256,
        since_timestamp: float = 0.0,
    ) -> List[CatalogEntry]:
        cursors = {str(k).lower(): str(v).lower() for k, v in (since_commit_cursors or {}).items()}
        rows: List[CatalogEntry] = []
        with self._lock:
            raw = [CatalogEntry.from_dict(row) for row in self._entries.values()]
        if namespace and namespace != "catalog/all":
            raw = filter_entries_by_namespace(raw, namespace)
        if interest and not interest.is_empty():
            raw = filter_entries_by_interest(raw, interest)
        for entry in raw:
            if float(since_timestamp or 0) > 0 and float(entry.updated_at) < float(since_timestamp):
                continue
            known = cursors.get(entry.graph_id.lower())
            if known and known == entry.latest_commit_id.lower():
                continue
            rows.append(entry)
        rows.sort(key=lambda item: (item.head_generation, item.updated_at), reverse=True)
        if limit > 0:
            return rows[:limit]
        return rows

    def bloom_keys_for_namespace(self, namespace: str = "catalog/system") -> List[str]:
        entries = self.list_entries(namespace=namespace, limit=0)
        keys: List[str] = []
        with self._lock:
            for entry in entries:
                keys.append(entry.graph_id)
                keys.append(entry.latest_commit_id)
                keys.append(entry.root_hash)
                keys.extend(self._chunk_hashes.get(entry.graph_id) or [])
        return keys

    def build_namespace_bloom(self, namespace: str = "catalog/system") -> Any:
        keys = self.bloom_keys_for_namespace(namespace)
        return build_bloom(keys, expected_entries=max(len(keys), DEFAULT_EXPECTED_ENTRIES))

    def bloom_summary(self, namespace: str = "catalog/system") -> BloomSummary:
        bloom = self.build_namespace_bloom(namespace)
        digest = hashlib.sha256(bloom.to_bytes()).hexdigest()
        entries = self.list_entries(namespace=namespace, limit=0)
        return BloomSummary(
            generation=self.generation,
            entry_count=len(entries),
            bit_count=bloom.size_bits,
            hash_count=bloom.hash_count,
            digest=digest,
            namespace=normalize_namespace(namespace),
        )

    def merge_remote_entries(self, entries: Iterable[CatalogEntry]) -> int:
        merged = 0
        for entry in entries:
            existing = self.get_entry(entry.graph_id)
            if existing and existing.head_generation >= entry.head_generation:
                if existing.latest_commit_id == entry.latest_commit_id:
                    continue
            chunk_hashes = list(entry.chunks) if entry.chunks else None
            self.upsert_entry(entry, chunk_hashes=chunk_hashes)
            merged += 1
        return merged

    def graph_ids(self) -> List[str]:
        with self._lock:
            return list(self._entries.keys())

    def status(self) -> Dict[str, Any]:
        summary = self.bloom_summary()
        m, k = compute_bloom_params(max(len(self.graph_ids()), 1))
        return {
            "generation": self.generation,
            "graph_count": len(self.graph_ids()),
            "bloom_bits": summary.bit_count,
            "bloom_hash_count": summary.hash_count,
            "bloom_digest": summary.digest,
            "target_fpr": DEFAULT_TARGET_FPR,
            "expected_entries": max(len(self.graph_ids()), DEFAULT_EXPECTED_ENTRIES),
            "computed_m": m,
            "computed_k": k,
        }
