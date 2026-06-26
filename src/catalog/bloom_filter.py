"""Simple Bloom filter for catalog chunk / graph presence hints."""

from __future__ import annotations

import base64
import hashlib
import math
from dataclasses import dataclass
from typing import Iterable


def _hash_indices(key: bytes, *, size_bits: int, hash_count: int) -> list[int]:
    digest = hashlib.sha256(key).digest()
    h1 = int.from_bytes(digest[:8], "big")
    h2 = int.from_bytes(digest[8:16], "big")
    indices: list[int] = []
    for i in range(hash_count):
        idx = (h1 + i * h2) % size_bits
        indices.append(idx)
    return indices


@dataclass
class BloomFilter:
    """Fixed-size Bloom filter (m bits, k hash functions)."""

    size_bits: int = 65536
    hash_count: int = 7
    bits: bytearray | None = None

    def __post_init__(self) -> None:
        if self.bits is None:
            byte_len = max(1, math.ceil(self.size_bits / 8))
            self.bits = bytearray(byte_len)

    def add(self, item: str | bytes) -> None:
        key = item if isinstance(item, bytes) else str(item).encode("utf-8")
        for idx in _hash_indices(key, size_bits=self.size_bits, hash_count=self.hash_count):
            byte_i, bit_i = divmod(idx, 8)
            self.bits[byte_i] |= 1 << bit_i

    def add_many(self, items: Iterable[str | bytes]) -> None:
        for item in items:
            self.add(item)

    def might_contain(self, item: str | bytes) -> bool:
        key = item if isinstance(item, bytes) else str(item).encode("utf-8")
        for idx in _hash_indices(key, size_bits=self.size_bits, hash_count=self.hash_count):
            byte_i, bit_i = divmod(idx, 8)
            if not (self.bits[byte_i] & (1 << bit_i)):
                return False
        return True

    def to_bytes(self) -> bytes:
        return bytes(self.bits)

    @classmethod
    def from_bytes(cls, raw: bytes, *, size_bits: int = 65536, hash_count: int = 7) -> "BloomFilter":
        bloom = cls(size_bits=size_bits, hash_count=hash_count, bits=bytearray(raw))
        return bloom

    def to_base64(self) -> str:
        return base64.b64encode(self.to_bytes()).decode("ascii")

    @classmethod
    def from_base64(cls, encoded: str, *, size_bits: int = 65536, hash_count: int = 7) -> "BloomFilter":
        raw = base64.b64decode(str(encoded or "").encode("ascii"))
        return cls.from_bytes(raw, size_bits=size_bits, hash_count=hash_count)

    def estimate_fill_ratio(self) -> float:
        set_bits = sum(bin(byte).count("1") for byte in self.bits)
        return set_bits / float(self.size_bits)
