"""Handshake guard — reject cognitive payloads at Device/Session boundary."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Set

from .constants import HANDSHAKE_FORBIDDEN_KEYS


def _collect_keys(obj: Any, *, prefix: str = "", depth: int = 0, max_depth: int = 4) -> Set[str]:
    if depth > max_depth:
        return set()
    keys: Set[str] = set()
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            norm = str(key).strip().lower()
            full = f"{prefix}.{norm}" if prefix else norm
            keys.add(norm)
            keys.add(full)
            keys.update(_collect_keys(value, prefix=full, depth=depth + 1, max_depth=max_depth))
    elif isinstance(obj, list):
        for item in obj[:16]:
            keys.update(_collect_keys(item, prefix=prefix, depth=depth + 1, max_depth=max_depth))
    return keys


def find_handshake_violations(payload: Mapping[str, Any]) -> list[str]:
    """Return forbidden cognitive keys present in a handshake payload."""
    present = _collect_keys(payload)
    violations = sorted(k for k in present if k.split(".")[-1] in HANDSHAKE_FORBIDDEN_KEYS)
    return violations


def assert_handshake_clean(payload: Mapping[str, Any]) -> None:
    violations = find_handshake_violations(payload)
    if violations:
        joined = ", ".join(violations[:8])
        raise ValueError(f"handshake must not carry cognitive data: {joined}")
