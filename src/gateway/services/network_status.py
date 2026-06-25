"""Connectivity, DHT, and firewall status for network observability routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class NetworkStatusHooks:
    get_connectivity_manager: Callable[[], Any]
    get_dht_service: Callable[[], Any]
    get_network_firewall: Callable[[], Any]


class NetworkStatusService:
    """Gateway-owned network stack snapshot still tied to app/network via hooks."""

    def __init__(self, hooks: NetworkStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        cm = self._hooks.get_connectivity_manager()
        dht = self._hooks.get_dht_service()
        fw = self._hooks.get_network_firewall()
        return {
            "connectivity": cm.status() if cm else {"enabled": False},
            "dht": dht.status() if dht else {"enabled": False},
            "firewall": fw.status() if fw else {"enabled": False},
        }

    def dht_status(self) -> Dict[str, Any]:
        dht = self._hooks.get_dht_service()
        return dht.status() if dht else {"enabled": False}
