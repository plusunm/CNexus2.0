"""BloomBuilder — compute (m, k) from target FPR and expected entry count."""

from __future__ import annotations

import math

from .bloom_filter import BloomFilter

DEFAULT_TARGET_FPR = 0.01
DEFAULT_EXPECTED_ENTRIES = 512
MIN_SIZE_BITS = 4096
MAX_SIZE_BITS = 524288


def compute_bloom_params(
    expected_entries: int,
    *,
    target_fpr: float = DEFAULT_TARGET_FPR,
) -> tuple[int, int]:
    """
    Choose bit array size m and hash count k for target false-positive rate.
    Uses optimal k ≈ (m/n) ln 2 once m is fixed from ln(FPR)/ln(0.618).
    """
    n = max(1, int(expected_entries))
    fpr = min(0.25, max(0.0001, float(target_fpr)))
    # m = -n * ln(fpr) / (ln 2)^2
    m = int(math.ceil(-n * math.log(fpr) / (math.log(2) ** 2)))
    m = max(MIN_SIZE_BITS, min(MAX_SIZE_BITS, m))
    k = max(1, int(round((m / n) * math.log(2))))
    k = min(k, 16)
    return m, k


def build_bloom(keys: list[str], *, expected_entries: int | None = None, target_fpr: float = DEFAULT_TARGET_FPR) -> BloomFilter:
    n = expected_entries if expected_entries is not None else max(len(keys), DEFAULT_EXPECTED_ENTRIES)
    size_bits, hash_count = compute_bloom_params(n, target_fpr=target_fpr)
    bloom = BloomFilter(size_bits=size_bits, hash_count=hash_count)
    bloom.add_many(keys)
    return bloom
