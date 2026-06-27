"""Peer registry + gossip snapshot for /api/peers and L0 status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .network_status import NetworkStatusService


@dataclass(frozen=True)
class PeersStatusHooks:
    peer_registry_path: Callable[[], str]
    get_peer_registry: Callable[[], Any]
    get_gossip_sync: Callable[[], Any]
    get_local_pubkey: Callable[[], str] = lambda: ""
    get_server_port: Callable[[], int] = lambda: 7864


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

    def build_discovered(self, *, refresh: bool = False) -> Dict[str, Any]:
        """All CNexus clients visible via registry, DHT, and optional LAN scan."""
        try:
            from network.discovered_clients import merge_discovered_clients
        except ImportError:
            from discovered_clients import merge_discovered_clients  # type: ignore

        reg = self._hooks.get_peer_registry()
        dht = self._network.get_dht_service()
        local_pubkey = str(self._hooks.get_local_pubkey() or "")
        port = int(self._hooks.get_server_port() or 7864)

        bootstrap_result: Optional[Dict[str, Any]] = None
        if refresh and dht is not None:
            if hasattr(dht, "bootstrap"):
                try:
                    bootstrap_result = dht.bootstrap()
                except Exception:
                    bootstrap_result = {"ok": False, "error": "bootstrap_failed"}

        lan_rows: List[Dict[str, Any]] = []
        lan_scan_ok = False
        if refresh:
            try:
                from network.host_config import lan_discovery_enabled
                from network.lan_discovery import scan_lan_cnexus_nodes

                if lan_discovery_enabled():
                    lan_rows = list(scan_lan_cnexus_nodes(port=port))
                    lan_scan_ok = True
                    if reg:
                        for row in lan_rows:
                            pubkey = str(row.get("pubkey") or "").strip()
                            host = str(row.get("host") or row.get("url") or "").strip()
                            if pubkey and host:
                                existing = reg.get_peer(pubkey)
                                status = str((existing or {}).get("status") or "discovered")
                                if status not in ("trusted", "online"):
                                    reg.save_peer(pubkey, host, status="discovered")
            except ImportError:
                pass

        dht_nodes: List[Dict[str, Any]] = []
        if dht is not None and hasattr(dht, "list_nodes"):
            dht_nodes = list(dht.list_nodes())

        registry_peers = reg.get_all_peers() if reg else {}
        clients = merge_discovered_clients(
            local_pubkey=local_pubkey,
            registry_peers=registry_peers,
            dht_nodes=dht_nodes,
            lan_rows=lan_rows,
        )

        trusted_count = sum(1 for row in clients if row.get("trusted"))
        online_count = sum(1 for row in clients if str(row.get("status") or "") == "online")

        return {
            "clients": clients,
            "count": len(clients),
            "trusted_count": trusted_count,
            "online_count": online_count,
            "discovered_count": sum(1 for row in clients if not row.get("trusted")),
            "refreshed": bool(refresh),
            "lan_scan_ok": lan_scan_ok,
            "lan_found": len(lan_rows),
            "dht_node_count": len(dht_nodes),
            "registry_count": len(registry_peers),
            "bootstrap": bootstrap_result,
        }
