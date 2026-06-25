#!/usr/bin/env python3
"""Cognitive provenance formatting tests."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.provenance import (  # noqa: E402
    PROVENANCE_AUDIT_PREVIEW,
    PROVENANCE_LOCAL_FULL,
    PROVENANCE_REMOTE_PREVIEW,
    format_llm_memory_fragment,
    provenance_from_block,
)


def main():
    local = {"data": {"content": "full local memory", "provenance": PROVENANCE_LOCAL_FULL}}
    assert provenance_from_block(local) == PROVENANCE_LOCAL_FULL
    assert "[Provenance:" not in format_llm_memory_fragment(
        "full local memory",
        provenance=PROVENANCE_LOCAL_FULL,
    )

    remote = {
        "data": {
            "content": "remote fragment",
            "replayed": True,
            "source_peer": "ab" * 32,
        }
    }
    assert provenance_from_block(remote) == PROVENANCE_REMOTE_PREVIEW
    tagged = format_llm_memory_fragment(
        "remote fragment",
        provenance=PROVENANCE_REMOTE_PREVIEW,
        source_peer="ab" * 32,
        block_id="mem-1",
    )
    assert "[Provenance: Remote-Preview]" in tagged
    assert "remote fragment" in tagged

    audit = {"data": {"content": "sync preview", "replayed": True}}
    assert provenance_from_block(audit) == PROVENANCE_AUDIT_PREVIEW
    tagged = format_llm_memory_fragment("sync preview", provenance=PROVENANCE_AUDIT_PREVIEW)
    assert "[Provenance: Audit-Preview]" in tagged

    print("PROVENANCE TEST PASSED")


if __name__ == "__main__":
    main()
