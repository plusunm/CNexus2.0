#!/usr/bin/env python3
"""Genesis entropy seed sync tests."""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.entropy import (  # noqa: E402
    EntropyStore,
    combine_entropy_seeds,
    derive_global_entropy,
    format_entropy_seed,
    parse_entropy_seed,
)
from core.identity_manager import IdentityManager  # noqa: E402
from core.peer_registry import PeerRegistry  # noqa: E402
from network.genesis_sync import GenesisSync  # noqa: E402
from network.gossip_sync import GossipSync  # noqa: E402


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_entropy_store_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "entropy.json")
        store_a = EntropyStore(path)
        local = store_a.local_seed()
        store_b = EntropyStore(path)
        assert store_b.local_seed() == local
        print("persisted:", store_a.local_seed_hex())


def test_global_entropy_xor():
    with tempfile.TemporaryDirectory() as tmp:
        store = EntropyStore(os.path.join(tmp, "entropy.json"))
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        reg.save_peer("aa" * 32, "http://127.0.0.1:9001", status="trusted")
        reg.update_peer("aa" * 32, entropy_seed="0x1111")
        reg.save_peer("bb" * 32, "http://127.0.0.1:9002", status="online")
        reg.update_peer("bb" * 32, entropy_seed="0x2222")

        expected = derive_global_entropy(
            local_seed=store.local_seed(),
            peer_seeds=[0x1111, 0x2222],
        )
        assert store.global_entropy(reg) == expected
        print("global:", store.global_entropy_hex(reg))


def test_genesis_handshake_exchanges_entropy():
    with tempfile.TemporaryDirectory() as tmp:
        log_a = os.path.join(tmp, "a.log")
        log_b = os.path.join(tmp, "b.log")
        key = os.path.join(tmp, "id.key")
        peers_b = os.path.join(tmp, "peers.json")
        entropy_b = os.path.join(tmp, "entropy-b.json")

        im = IdentityManager(key)
        audit_a = AuditLog(log_a)
        audit_b = AuditLog(log_b)
        for i in range(3):
            audit_a.log(im, {"event": "test.genesis", "n": i})

        remote_entries = list(audit_a.iter_entries())
        store_b = EntropyStore(entropy_b)
        reg_b = PeerRegistry(peers_b)

        def fake_urlopen(req, timeout=10):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if url.endswith("/api/peer/sync"):
                body = json.loads(req.data.decode("utf-8"))
                assert body.get("protocol_version") == "2.0"
                assert body.get("entropy_seed")
                return _FakeResponse({
                    "ok": True,
                    "protocol_version": "2.0",
                    "entropy_seed": "0xABCDEF0123456789",
                    "last_hash": audit_a.last_hash,
                    "audit_entries": audit_a.entry_count(),
                    "integrity_ok": True,
                    "global_entropy": "0xdeadbeef",
                })
            if "/api/peer/audit" in url:
                return _FakeResponse({
                    "ok": True,
                    "anchor_found": True,
                    "entries": remote_entries,
                    "last_hash": audit_a.last_hash,
                    "has_more": False,
                })
            raise RuntimeError(f"unexpected url {url}")

        import urllib.request as urlrequest

        original_urlopen = urlrequest.urlopen
        try:
            urlrequest.urlopen = fake_urlopen

            gossip_b = GossipSync(audit_b, im, None)
            gossip_b.attach_peer_registry(reg_b)
            genesis = GenesisSync(gossip_b, enabled=True, jitter_min=0, jitter_max=0, chunk_size=200)
            genesis.attach_entropy(store_b)
            gossip_b.attach_genesis(genesis)

            result = genesis.genesis_handshake("http://127.0.0.1:9001", peer_pubkey="peer-test")
            assert result.get("ok"), result
            assert result.get("head_probe", {}).get("peer_entropy_recorded") == "0xabcdef0123456789"
            peer_row = reg_b.get_peer("peer-test") or {}
            assert peer_row.get("entropy_seed") == "0xabcdef0123456789"
            assert audit_b.last_hash == audit_a.last_hash
            print("genesis_entropy:", result.get("head_probe", {}).get("global_entropy"))
        finally:
            urlrequest.urlopen = original_urlopen


def main():
    test_entropy_store_persistence()
    test_global_entropy_xor()
    test_genesis_handshake_exchanges_entropy()
    print("\nGENESIS ENTROPY SYNC TEST PASSED")


if __name__ == "__main__":
    main()
