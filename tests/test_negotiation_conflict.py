#!/usr/bin/env python3
"""Negotiation → conflict bridge tests."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.negotiation_conflict import (  # noqa: E402
    find_memory_block_conflicts,
    format_negotiation_conflict_context,
    memory_rows_from_audit_entries,
)


def _entry(block_id: str, preview: str):
    return {
        "hash": f"h-{block_id}",
        "data": {
            "event": "memory.block",
            "block_id": block_id,
            "content_preview": preview,
            "label": "episode",
        },
    }


def main():
    local = [_entry("mem-1", "earth is flat"), _entry("mem-2", "same")]
    remote = [_entry("mem-1", "earth is round"), _entry("mem-2", "same")]

    rows = memory_rows_from_audit_entries(local)
    assert rows["mem-1"]["content"] == "earth is flat"

    conflicts = find_memory_block_conflicts(local, remote)
    assert len(conflicts) == 1
    assert conflicts[0][0]["block_id"] == "mem-1"

    ctx = format_negotiation_conflict_context([
        {
            "peer_pubkey": "aa" * 32,
            "negotiation_error": "commit_failed",
            "global_entropy": "0x1234",
            "resolutions": [
                {"status": "forked", "fork": {"local": "A", "remote": "B"}},
            ],
        }
    ])
    assert "negotiation conflicts" in ctx
    assert "[forked]" in ctx
    print("conflicts:", len(conflicts))
    print("\nNEGOTIATION CONFLICT TEST PASSED")


if __name__ == "__main__":
    main()
