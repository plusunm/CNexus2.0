"""Tests for LAN discovery helpers."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from network.host_config import list_lan_ipv4, resolve_bind_host, resolve_public_url  # noqa: E402
from network.lan_discovery import find_peer_on_lan, scan_lan_cnexus_nodes  # noqa: E402


def test_resolve_bind_host_defaults_open():
    os.environ.pop("CNEXUS_BIND_HOST", None)
    os.environ["CNEXUS_AUTO_NETWORK"] = "1"
    assert resolve_bind_host() == "0.0.0.0"


def test_find_peer_on_lan_with_probe():
    target = "aa" * 32

    def probe(url: str, timeout: float = 0.35):
        if url.endswith(":7864"):
            return target
        return None

    rows = scan_lan_cnexus_nodes(
        port=7864,
        local_ips=["192.168.1.10"],
        timeout=0.1,
        probe=probe,
    )
    assert any(row["pubkey"] == target for row in rows)
    url = find_peer_on_lan(target, port=7864, local_ips=["192.168.1.10"], probe=probe)
    assert url and url.startswith("http://192.168.1.") and url.endswith(":7864")


def main():
    test_resolve_bind_host_defaults_open()
    test_find_peer_on_lan_with_probe()
    ips = list_lan_ipv4()
    assert isinstance(ips, list)
    pub = resolve_public_url(7864)
    assert pub == "" or pub.startswith("http://")
    print("LAN DISCOVERY TEST PASSED")


if __name__ == "__main__":
    main()
