"""Chunk verification — truth from bytes, never from Manifest."""

from __future__ import annotations

from typing import Optional

try:
    from protocol.ids import compute_chunk_hash, normalize_hash64
except ImportError:
    from cnexus_protocol.ids import compute_chunk_hash, normalize_hash64


class ChunkVerifyError(ValueError):
    """Raised when chunk bytes do not match declared hash."""


class ChunkImmutableError(ValueError):
    """Raised when an existing chunk would be overwritten with different bytes."""


def verify_chunk_bytes(content: bytes, chunk_hash: str) -> bool:
    """
    Independent peer-verifiable check: SHA256(bytes) == chunk_hash.
    Manifest does NOT participate in this check.
    """
    if not content:
        return False
    expected = normalize_hash64(str(chunk_hash or ""), field="chunk_hash")
    actual = compute_chunk_hash(content)
    return actual == expected


def assert_chunk_bytes(content: bytes, chunk_hash: str) -> str:
    """Verify and return normalized chunk_hash, or raise ChunkVerifyError."""
    expected = normalize_hash64(str(chunk_hash or ""), field="chunk_hash")
    actual = compute_chunk_hash(content)
    if actual != expected:
        raise ChunkVerifyError(f"chunk hash mismatch: expected {expected}, got {actual}")
    return expected


def verify_or_compute(content: bytes, *, expected_hash: str = "") -> str:
    """
    Put-path helper: if expected_hash given, verify bytes independently.
    Otherwise return computed hash (content defines truth).
    """
    actual = compute_chunk_hash(content)
    if expected_hash:
        expected = normalize_hash64(expected_hash, field="chunk_hash")
        if actual != expected:
            raise ChunkVerifyError(f"chunk hash mismatch: expected {expected}, got {actual}")
    return actual
