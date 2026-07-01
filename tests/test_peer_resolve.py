#!/usr/bin/env python3
"""Peer resolve tests (device-ID-only connect)."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.founder_peers import BOOTSTRAP_TRUSTED_PEERS  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from core.peer_registry import PeerRegistry  # noqa: E402
from core.peer_resolve import resolve_peer_host  # noqa: E402


def test_resolve_hub_from_bootstrap():
    hub = str(BOOTSTRAP_TRUSTED_PEERS[0]["pubkey"])
    host, source = resolve_peer_host(hub, remote_resolve=False)
    assert source == "bootstrap"
    assert host == BOOTSTRAP_TRUSTED_PEERS[0]["host"]


def test_resolve_from_registry():
    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        im = IdentityManager(os.path.join(tmp, "local.key"))
        target = "aa" * 32
        reg.save_peer(target, "http://10.0.0.5:7864", status="trusted")
        host, source = resolve_peer_host(
            target,
            peer_registry=reg,
            local_pubkey=im.public_key_hex(),
            remote_resolve=False,
        )
        assert source == "registry"
        assert host == "http://10.0.0.5:7864"


def test_resolve_skips_self():
    with tempfile.TemporaryDirectory() as tmp:
        im = IdentityManager(os.path.join(tmp, "local.key"))
        local = im.public_key_hex()
        host, source = resolve_peer_host(
            local,
            local_pubkey=local,
            local_public_url="http://127.0.0.1:7864",
            remote_resolve=False,
        )
        assert source == "self"
        assert host == "http://127.0.0.1:7864"


if __name__ == "__main__":
    test_resolve_hub_from_bootstrap()
    test_resolve_from_registry()
    test_resolve_skips_self()
    print("peer_resolve tests OK")
