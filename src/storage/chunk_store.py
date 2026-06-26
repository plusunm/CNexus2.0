"""ChunkStore — content-addressed immutable local KV (P4.0)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from protocol.ids import compute_chunk_hash, normalize_hash64
except ImportError:
    from cnexus_protocol.ids import compute_chunk_hash, normalize_hash64

from .chunk_verifier import ChunkImmutableError, ChunkVerifyError, assert_chunk_bytes, verify_chunk_bytes


class ChunkStore:
    """
    Local content-addressed chunk store.

    Iron rules (P4):
      ① key = SHA256(bytes)
      ② immutable — never overwrite existing blob with different bytes
      ③ peer-verifiable — verify() checks bytes→hash, not manifest
      ④ multi-source safe — same hash from any source is identical blob
    """

    def __init__(self, chunks_dir: str | Path = "data/chunks"):
        self.chunks_dir = Path(chunks_dir)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path_for(self, chunk_hash: str) -> Path:
        digest = normalize_hash64(str(chunk_hash or ""), field="chunk_hash")
        return self.chunks_dir / digest[:2] / digest

    def put(self, content: bytes, *, expected_hash: str = "") -> str:
        """
        Store chunk bytes after independent hash verification.
        Returns content-addressed chunk_hash.
        """
        if not content:
            raise ChunkVerifyError("empty chunk content rejected")
        chunk_hash = assert_chunk_bytes(content, expected_hash) if expected_hash else compute_chunk_hash(content)
        path = self._path_for(chunk_hash)
        with self._lock:
            if path.exists():
                stored = path.read_bytes()
                if stored != content:
                    raise ChunkImmutableError(f"chunk {chunk_hash} already exists with different bytes")
                return chunk_hash
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return chunk_hash

    def get(self, chunk_hash: str) -> Optional[bytes]:
        path = self._path_for(chunk_hash)
        if not path.exists():
            return None
        return path.read_bytes()

    def has(self, chunk_hash: str) -> bool:
        return self._path_for(chunk_hash).exists()

    def verify(self, chunk_hash: str, *, content: Optional[bytes] = None) -> bool:
        """
        Verify chunk truth from bytes→hash.
        If content omitted, reads stored blob and verifies independently.
        """
        if content is not None:
            return verify_chunk_bytes(content, chunk_hash)
        stored = self.get(chunk_hash)
        if stored is None:
            return False
        return verify_chunk_bytes(stored, chunk_hash)

    def delete(self, chunk_hash: str) -> bool:
        """Local admin only — not used in normal publish path."""
        path = self._path_for(chunk_hash)
        with self._lock:
            if not path.exists():
                return False
            path.unlink()
            return True

    def status(self) -> Dict[str, Any]:
        count = 0
        total_bytes = 0
        if self.chunks_dir.exists():
            for path in self.chunks_dir.rglob("*"):
                if path.is_file():
                    count += 1
                    total_bytes += path.stat().st_size
        return {
            "chunk_count": count,
            "total_bytes": total_bytes,
            "chunks_dir": str(self.chunks_dir),
        }
