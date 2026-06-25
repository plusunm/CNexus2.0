#!/usr/bin/env python3
"""Cognitive pruning engine tests."""

import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.cognitive_pruning import CognitivePruningEngine  # noqa: E402
from kernel.block_store import BlockStore  # noqa: E402


def _block(block_id: str, content: str, *, label: str = "episode", age_seconds: float = 86400 * 10):
    return {
        "block_id": block_id,
        "label": label,
        "timestamp": time.time() - age_seconds,
        "data": {"content": content, "label": label},
    }


def main():
    engine_state: dict = {}
    store = BlockStore()
    store.add(_block("hot-1", "referenced memory", age_seconds=86400 * 30))
    store.add(_block("cold-1", "never referenced", age_seconds=86400 * 30))
    store.add(_block("dispute-1", "contested fact", age_seconds=86400 * 2))

    with tempfile.TemporaryDirectory() as tmp:
        engine = CognitivePruningEngine(engine_state, store, archive_dir=tmp)
        engine.cold_min_age = 86400
        engine.conflict_summary_threshold = 2

        engine.record_block_reference("hot-1")
        engine.record_conflict_block("dispute-1")
        engine.record_conflict_block("dispute-1")

        report = engine.run_cycle(dry_run=False)
        assert report["ok"] is True
        assert report["summaries_created"] == 1
        assert report["archived_blocks"] == 1

        active_ids = {block.get("block_id") for block in store.blocks}
        assert "cold-1" not in active_ids
        assert "hot-1" in active_ids
        assert any(str(block_id).startswith("kc-dispute-1") for block_id in active_ids)

        status = engine.status()
        assert status["active_blocks"] >= 2
        assert status["total_archived"] == 1
        assert status["total_summarized"] == 1

    print("\nCOGNITIVE PRUNING TEST PASSED")


if __name__ == "__main__":
    main()
