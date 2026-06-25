#!/usr/bin/env python3
"""Peer trust gate tests."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from api.peer_trust import verify_inbound_peer_trust  # noqa: E402
from core.peer_registry import PeerRegistry  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, super().get(key.lower(), default))


def main():
    os.environ["CNEXUS_PEER_TRUST_REQUIRED"] = "1"
    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        im = IdentityManager(os.path.join(tmp, "local.key"))
        pubkey = im.public_key_hex()
        headers = _Headers({"X-CNexus-Pubkey": pubkey})

        ok, err, status = verify_inbound_peer_trust("/api/asset/receive", headers, reg)
        assert not ok and status == 403, (ok, err, status)

        reg.save_peer(pubkey, "http://127.0.0.1:7864", status="trusted")
        ok, err, status = verify_inbound_peer_trust("/api/asset/receive", headers, reg)
        assert ok, (err, status)

        ok, err, status = verify_inbound_peer_trust(
            "/api/peer/audit",
            headers,
            reg,
            method="GET",
        )
        assert ok, (err, status)

        ok, err, status = verify_inbound_peer_trust("/api/p2p/handshake", headers, reg)
        assert ok, (err, status)

        os.environ["CNEXUS_PEER_TRUST_REQUIRED"] = "0"
        reg.remove_peer(pubkey)
        ok, err, status = verify_inbound_peer_trust("/api/asset/receive", headers, reg)
        assert ok, (err, status)

    print("PEER TRUST TEST PASSED")


if __name__ == "__main__":
    main()
