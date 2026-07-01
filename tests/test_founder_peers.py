#!/usr/bin/env python3
"""Founder peer bootstrap tests."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.founder_peers import (  # noqa: E402
    BOOTSTRAP_TRUSTED_PEERS,
    bootstrap_host_for_pubkey,
    ensure_bootstrap_peers,
)
from core.identity_manager import IdentityManager  # noqa: E402
from core.peer_registry import PeerRegistry  # noqa: E402


def test_seeds_bootstrap_peers_on_empty_registry():
    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        im = IdentityManager(os.path.join(tmp, "other.key"))
        local = im.public_key_hex()
        hub = str(BOOTSTRAP_TRUSTED_PEERS[0]["pubkey"])
        founder = str(BOOTSTRAP_TRUSTED_PEERS[1]["pubkey"])
        assert hub != local and founder != local

        added = ensure_bootstrap_peers(reg, local)
        assert hub in added and founder in added
        hub_row = reg.get_peer(hub)
        founder_row = reg.get_peer(founder)
        assert hub_row is not None and founder_row is not None
        assert hub_row.get("label") == "hub"
        assert hub_row.get("host") == BOOTSTRAP_TRUSTED_PEERS[0]["host"]
        assert founder_row.get("label") == "founder"
        assert founder_row.get("host") == ""

        added_again = ensure_bootstrap_peers(reg, local)
        assert added_again == []


def test_skips_when_local_is_hub():
    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        hub = str(BOOTSTRAP_TRUSTED_PEERS[0]["pubkey"])
        added = ensure_bootstrap_peers(reg, hub)
        assert hub not in added
        assert reg.get_peer(hub) is None
        founder = str(BOOTSTRAP_TRUSTED_PEERS[1]["pubkey"])
        assert founder in added


def test_skips_when_local_is_founder():
    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        founder = str(BOOTSTRAP_TRUSTED_PEERS[1]["pubkey"])
        added = ensure_bootstrap_peers(reg, founder)
        assert founder not in added
        assert reg.get_peer(founder) is None
        hub = str(BOOTSTRAP_TRUSTED_PEERS[0]["pubkey"])
        assert hub in added


def test_readds_after_manual_removal():
    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        im = IdentityManager(os.path.join(tmp, "other.key"))
        hub = str(BOOTSTRAP_TRUSTED_PEERS[0]["pubkey"])
        ensure_bootstrap_peers(reg, im.public_key_hex())
        reg.remove_peer(hub)
        added = ensure_bootstrap_peers(reg, im.public_key_hex())
        assert hub in added
        assert reg.get_peer(hub) is not None


def test_bootstrap_host_for_hub():
    hub = str(BOOTSTRAP_TRUSTED_PEERS[0]["pubkey"])
    assert bootstrap_host_for_pubkey(hub) == BOOTSTRAP_TRUSTED_PEERS[0]["host"]
    founder = str(BOOTSTRAP_TRUSTED_PEERS[1]["pubkey"])
    assert bootstrap_host_for_pubkey(founder) == ""


if __name__ == "__main__":
    test_seeds_bootstrap_peers_on_empty_registry()
    test_skips_when_local_is_hub()
    test_skips_when_local_is_founder()
    test_readds_after_manual_removal()
    test_bootstrap_host_for_hub()
    print("founder_peers tests OK")
