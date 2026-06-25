"""Asset pipeline / vector index status for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class AssetsStatusHooks:
    asset_embed_enabled: Callable[[], bool]
    clip_enabled: Callable[[], bool]
    asset_peer_push_enabled: Callable[[], bool]
    asset_peer_pull_enabled: Callable[[], bool]
    get_asset_vector_index: Callable[[], Any]
    get_asset_peer_sync: Callable[[], Any]
    get_asset_push_queue: Callable[[], Any]
    get_asset_processor: Callable[[], Any]


class AssetsStatusService:
    def __init__(self, hooks: AssetsStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        idx = self._hooks.get_asset_vector_index()
        sync = self._hooks.get_asset_peer_sync()
        queue = self._hooks.get_asset_push_queue()
        proc = self._hooks.get_asset_processor()
        return {
            "embed_enabled": self._hooks.asset_embed_enabled(),
            "clip_enabled": self._hooks.clip_enabled(),
            "peer_push_enabled": self._hooks.asset_peer_push_enabled(),
            "peer_pull_enabled": self._hooks.asset_peer_pull_enabled(),
            "vector_index": idx.status() if idx else {"enabled": False},
            "peer_sync": sync.status() if sync else {"peer_count": 0},
            "push_retry_queue": queue.status() if queue else {"enabled": False},
            "local_assets": len(proc.list_assets(limit=500)) if proc else 0,
        }
