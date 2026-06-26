"""Canonical serialization for protocol objects — stable bytes for hashing and wire."""

from __future__ import annotations

import json
from typing import Any, Mapping


def canonical_json(obj: Mapping[str, Any]) -> str:
    """Deterministic JSON: sorted keys, compact separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def to_bytes(obj: Mapping[str, Any]) -> bytes:
    return canonical_json(obj).encode("utf-8")


def from_bytes(raw: bytes) -> dict[str, Any]:
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("protocol object must decode to a JSON object")
    return data
