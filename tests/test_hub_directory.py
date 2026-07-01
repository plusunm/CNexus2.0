#!/usr/bin/env python3
"""Hub directory tests."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.hub_directory import HubDirectory  # noqa: E402


def test_register_and_resolve():
    with tempfile.TemporaryDirectory() as tmp:
        hub = HubDirectory(os.path.join(tmp, "hub_directory.json"))
        pubkey = "aa" * 32
        row = hub.register(pubkey, "http://203.0.113.10:7864", endpoints=["http://10.0.0.5:7864"], label="client")
        assert row["host"] == "http://203.0.113.10:7864"
        resolved = hub.resolve(pubkey)
        assert resolved is not None
        assert resolved["host"] == "http://203.0.113.10:7864"
        listed = hub.list_peers()
        assert len(listed) == 1


if __name__ == "__main__":
    test_register_and_resolve()
    print("hub_directory tests OK")
