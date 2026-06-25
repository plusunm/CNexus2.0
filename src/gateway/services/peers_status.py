"""Peer registry + gossip snapshot for /api/peers and L0 status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from .network_status import NetworkStatusService


@dataclass(frozen=True)
class PeersStatusHooks:
    peer_registry_path: Callable[[], str]
    get_peer_registry: Callable[[], Any]
    get_gossip_sync: Callable[[], Any]


class PeersStatusService:
    """Gateway-owned peers overview still tied to core/network via hooks."""

    def __init__(self, hooks: PeersStatusHooks, network: NetworkStatusService):
        self._hooks = hooks
        self._network = network

    def build(self) -> Dict[str, Any]:
        reg = self._hooks.get_peer_registry()
        gossip = self._hooks.get_gossip_sync()
        return {
            "registry_path": self._hooks.peer_registry_path(),
            "peer_count": len(reg.get_all_peers()) if reg else 0,
            "peers": reg.get_all_peers() if reg else {},
            "gossip_recent": gossip.recent_results() if gossip else {},
            "network": self._network.build(),
        }
