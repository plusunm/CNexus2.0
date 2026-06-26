"""ChunkDescriptor index — network contract metadata (NOT Manifest)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from protocol.models import ChunkDescriptor
except ImportError:
    from cnexus_protocol.models import ChunkDescriptor


class DescriptorStore:
    """Persist ChunkDescriptor by content hash — tracks provenance, not payload truth."""

    def __init__(self, storage_path: str | Path = "data/chunk_descriptors.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._rows: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                self._rows = dict(data.get("descriptors") or {})
        except Exception:
            self._rows = {}

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump({"descriptors": self._rows}, handle, ensure_ascii=False, indent=2)

    def get(self, chunk_hash: str) -> Optional[ChunkDescriptor]:
        row = self._rows.get(str(chunk_hash or "").strip().lower())
        if not row:
            return None
        return ChunkDescriptor.from_dict(row)

    def save(
        self,
        descriptor: ChunkDescriptor,
        *,
        verifier_peer_id: str = "",
        source_peer_id: str = "",
    ) -> ChunkDescriptor:
        key = descriptor.chunk_hash
        with self._lock:
            existing = self._rows.get(key)
            verified = set(descriptor.verified_by)
            sources = set(descriptor.sources)
            created_by = descriptor.created_by
            if existing:
                prev = ChunkDescriptor.from_dict(existing)
                verified.update(prev.verified_by)
                sources.update(prev.sources)
                if not created_by:
                    created_by = prev.created_by
            if verifier_peer_id:
                verified.add(verifier_peer_id.strip().lower())
            if source_peer_id:
                sources.add(source_peer_id.strip().lower())
            merged = ChunkDescriptor(
                chunk_hash=descriptor.chunk_hash,
                size=int(descriptor.size),
                encoding=descriptor.encoding,
                compression=descriptor.compression,
                created_by=created_by,
                verified_by=tuple(sorted(verified)),
                sources=tuple(sorted(sources)),
            )
            self._rows[key] = merged.to_dict()
            self._persist()
        return merged

    def list_hashes(self) -> List[str]:
        with self._lock:
            return list(self._rows.keys())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {"descriptor_count": len(self._rows)}
