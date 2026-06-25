"""Network-wide consensus entropy — XOR mix of local + trusted peer seeds."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROTOCOL_VERSION = "2.0"
ENTROPY_MASK = (1 << 64) - 1


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def entropy_sync_enabled() -> bool:
    return _env_truthy("CNEXUS_ENTROPY_SYNC", default=True)


def parse_entropy_seed(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return int(value) & ENTROPY_MASK
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.lower().startswith("0x"):
            return int(text, 16) & ENTROPY_MASK
        return int(text) & ENTROPY_MASK
    except (TypeError, ValueError):
        return None


def format_entropy_seed(seed: int) -> str:
    return hex(int(seed or 0) & ENTROPY_MASK)


def peer_entropy_seed(pubkey: str) -> int:
    """Deterministic fallback before a peer's genesis seed is synchronized."""
    pubkey = str(pubkey or "").strip()
    if not pubkey:
        return 0
    digest = hashlib.sha256(pubkey.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) & ENTROPY_MASK


def combine_entropy_seeds(*seeds: int) -> int:
    value = 0
    for seed in seeds:
        value ^= int(seed or 0)
    return value & ENTROPY_MASK


def derive_global_entropy(
    *,
    local_seed: int,
    peer_seeds: Optional[List[int]] = None,
    peer_pubkeys: Optional[List[str]] = None,
) -> int:
    seeds = [int(local_seed or 0) & ENTROPY_MASK]
    if peer_seeds:
        seeds.extend(int(s) & ENTROPY_MASK for s in peer_seeds if s is not None)
    elif peer_pubkeys:
        seeds.extend(peer_entropy_seed(pubkey) for pubkey in peer_pubkeys if pubkey)
    return combine_entropy_seeds(*seeds)


def temperature_from_seed(seed: int, *, base: float = 0.7, spread: float = 0.3) -> float:
    bucket = int(seed or 0) % 1000
    return round(base + (bucket / 1000.0) * spread, 3)


def collect_trusted_peer_seeds(peer_registry) -> List[int]:
    if peer_registry is None:
        return []
    rows = peer_registry.get_all_peers()
    seeds: List[int] = []
    for pubkey, row in rows.items():
        if str(row.get("status") or "").strip() not in ("trusted", "online"):
            continue
        parsed = parse_entropy_seed(row.get("entropy_seed"))
        if parsed is not None:
            seeds.append(parsed)
        elif pubkey:
            seeds.append(peer_entropy_seed(pubkey))
    return seeds


class EntropyStore:
    """Persist local entropy seed and derive mesh-wide consensus entropy."""

    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict) and data.get("local_seed") is not None:
                    parsed = parse_entropy_seed(data.get("local_seed"))
                    if parsed is not None:
                        return {
                            "local_seed": parsed,
                            "created_at": float(data.get("created_at") or time.time()),
                            "protocol_version": str(data.get("protocol_version") or PROTOCOL_VERSION),
                        }
            except Exception:
                pass
        seed = int.from_bytes(os.urandom(8), "big") & ENTROPY_MASK
        state = {
            "local_seed": seed,
            "created_at": time.time(),
            "protocol_version": PROTOCOL_VERSION,
        }
        self._persist_state(state)
        return state

    def _persist_state(self, state: Dict[str, Any]):
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "local_seed": format_entropy_seed(int(state["local_seed"])),
                    "created_at": state.get("created_at"),
                    "protocol_version": state.get("protocol_version", PROTOCOL_VERSION),
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )

    def local_seed(self) -> int:
        with self._lock:
            return int(self._state.get("local_seed") or 0) & ENTROPY_MASK

    def local_seed_hex(self) -> str:
        return format_entropy_seed(self.local_seed())

    def global_entropy(self, peer_registry=None) -> int:
        peer_seeds = collect_trusted_peer_seeds(peer_registry)
        return derive_global_entropy(local_seed=self.local_seed(), peer_seeds=peer_seeds)

    def global_entropy_hex(self, peer_registry=None) -> str:
        return format_entropy_seed(self.global_entropy(peer_registry))

    def record_peer_seed(self, peer_registry, pubkey: str, seed_value: Any) -> Optional[str]:
        pubkey = str(pubkey or "").strip()
        parsed = parse_entropy_seed(seed_value)
        if not pubkey or parsed is None or peer_registry is None:
            return None
        formatted = format_entropy_seed(parsed)
        if not peer_registry.get_peer(pubkey):
            peer_registry.save_peer(pubkey, "", status="online")
        row = peer_registry.update_peer(
            pubkey,
            entropy_seed=formatted,
            entropy_synced_at=time.time(),
        )
        return formatted if row else None

    def genesis_payload_fields(self) -> Dict[str, str]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "entropy_seed": self.local_seed_hex(),
        }

    def status(self, peer_registry=None) -> Dict[str, Any]:
        peer_seeds = collect_trusted_peer_seeds(peer_registry)
        global_seed = self.global_entropy(peer_registry)
        return {
            "enabled": entropy_sync_enabled(),
            "protocol_version": PROTOCOL_VERSION,
            "local_seed": self.local_seed_hex(),
            "global_entropy": format_entropy_seed(global_seed),
            "temperature": temperature_from_seed(global_seed),
            "trusted_peer_seeds": len(peer_seeds),
            "path": str(self.storage_path),
        }
