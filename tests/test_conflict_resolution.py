#!/usr/bin/env python3
"""ConflictResolutionAgent heuristic tests."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.entropy import (  # noqa: E402
    combine_entropy_seeds,
    derive_global_entropy,
    peer_entropy_seed,
    temperature_from_seed,
)
from core.conflict_resolution import (  # noqa: E402
    ConflictResolutionAgent,
    apply_resolution_to_block,
    entries_conflict,
    entry_from_audit_data,
    entry_from_block,
)


def test_entropy_deterministic():
    a = peer_entropy_seed("aa" * 32)
    b = peer_entropy_seed("bb" * 32)
    seed = combine_entropy_seeds(a, b, 42)
    assert seed == combine_entropy_seeds(a, b, 42)
    temp = temperature_from_seed(seed)
    assert 0.7 <= temp <= 1.0
    print("entropy:", hex(seed), "temp:", temp)


def test_aligned_entries():
    agent = ConflictResolutionAgent()
    local = {"block_id": "mem-1", "content": "same fact", "source": "local"}
    remote = {"block_id": "mem-1", "content": "same fact", "source": "remote"}
    assert not entries_conflict(local, remote)
    report = agent.resolve(local, remote, mode="precision", use_llm=False)
    assert report.get("ok") and report.get("status") == "aligned"
    print("aligned:", report.get("status"))


def test_precision_fork():
    agent = ConflictResolutionAgent()
    local = {"block_id": "mem-2", "content": "地球是平的", "source": "local"}
    remote = {"block_id": "mem-2", "content": "地球是圆的", "source": "remote", "source_peer": "cc" * 32}
    report = agent.resolve(local, remote, mode="precision", use_llm=False, seed=12345)
    assert report.get("ok") and report.get("status") == "forked"
    assert report.get("fork", {}).get("local")
    print("precision_fork:", report.get("rationale"))


def test_emergent_heuristic_merge():
    agent = ConflictResolutionAgent()
    local = {"block_id": "mem-3", "content": "CNexus 是个人认知助手", "source": "local"}
    remote = {
        "block_id": "mem-3",
        "content": "CNexus 是个人认知助手，支持 P2P 同步",
        "source": "remote",
    }
    report = agent.resolve(local, remote, mode="emergent", use_llm=False, seed=99)
    assert report.get("ok") and report.get("status") == "merged"
    print("emergent_merge:", report.get("status"))


def test_apply_resolution_to_block():
    block = {
        "block_id": "mem-4",
        "label": "episode",
        "data": {"content": "old", "provenance": "local-full"},
    }
    resolution = {
        "ok": True,
        "status": "merged",
        "merged_content": "new merged fact",
        "rationale": "test",
    }
    updated = apply_resolution_to_block(block, resolution)
    assert updated["data"]["content"] == "new merged fact"
    assert updated["data"]["conflict_status"] == "merged"
    print("apply_block:", updated["label"])


def test_entry_helpers():
    block = {"block_id": "x", "label": "episode", "data": {"content": "hello"}}
    audit = {"block_id": "x", "content_preview": "world", "source_peer": "dd" * 32}
    local = entry_from_block(block)
    remote = entry_from_audit_data(audit)
    assert local["content"] == "hello"
    assert remote["content"] == "world"
    assert entries_conflict(local, remote)
    print("entry_helpers: ok")


def test_replay_conflict_hook_shape():
    os.environ["CNEXUS_CONFLICT_RESOLUTION"] = "1"
    from core.log_replay import LogReplayEngine  # noqa: E402

    class _Store:
        blocks = [
            {
                "block_id": "replay-1",
                "label": "episode",
                "data": {"content": "version A"},
            }
        ]

    calls = []

    def handler(existing, incoming, ts):
        calls.append((existing["block_id"], incoming.get("content_preview")))
        return {"applied": True, "canonical_content": "version B merged"}

    engine = LogReplayEngine(conflict_handler=handler)
    report = {"conflicts": 0, "conflicts_resolved": 0}
    seen_blocks = {"replay-1": "version a"}
    applied = engine._apply_memory_block(
        {"block_id": "replay-1", "content_preview": "version B"},
        _Store,
        seen_blocks,
        1.0,
        report,
    )
    assert applied is True
    assert report["conflicts"] == 1
    assert report["conflicts_resolved"] == 1
    assert calls
    print("replay_hook:", report)


def main():
    test_entropy_deterministic()
    test_aligned_entries()
    test_precision_fork()
    test_emergent_heuristic_merge()
    test_apply_resolution_to_block()
    test_entry_helpers()
    test_replay_conflict_hook_shape()
    print("\nCONFLICT RESOLUTION TEST PASSED")


if __name__ == "__main__":
    main()
