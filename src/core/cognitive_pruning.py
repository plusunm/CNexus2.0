"""Cognitive pruning — frequency-based forgetting and dispute summarization."""

from __future__ import annotations

import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class CognitivePruningEngine:
    """Archive cold, unreferenced memory blocks and compress recurring dispute points."""

    PROTECT_LABELS = frozenset({"persona", "emotion", "knowledge_conclusion", "semantic"})

    def __init__(
        self,
        engine_state: dict,
        block_store,
        *,
        archive_dir: str | Path,
        audit_fn: Optional[Callable[[str, dict], Any]] = None,
    ):
        self.engine_state = engine_state
        self.block_store = block_store
        self.archive_dir = Path(archive_dir)
        self.audit_fn = audit_fn
        self.enabled = _env_bool("CNEXUS_COGNITIVE_PRUNING", True)
        self.cold_min_age = _env_int("CNEXUS_PRUNE_COLD_AGE_SECONDS", 7 * 86400)
        self.conflict_summary_threshold = _env_int("CNEXUS_PRUNE_CONFLICT_THRESHOLD", 3)
        self.max_archive_per_run = _env_int("CNEXUS_PRUNE_BATCH", 24)

    def _meta(self) -> dict:
        return self.engine_state.setdefault(
            "cognitive_prune",
            {
                "ref_counts": {},
                "conflict_counts": {},
                "archived_block_ids": [],
                "knowledge_conclusions": [],
                "last_run_at": 0,
                "last_report": None,
                "total_archived": 0,
                "total_summarized": 0,
            },
        )

    def record_block_reference(self, block_id: str) -> None:
        block_id = str(block_id or "").strip()
        if not block_id:
            return
        counts = self._meta().setdefault("ref_counts", {})
        counts[block_id] = int(counts.get(block_id) or 0) + 1

    def record_conflict_block(self, block_id: str) -> None:
        block_id = str(block_id or "").strip()
        if not block_id:
            return
        counts = self._meta().setdefault("conflict_counts", {})
        counts[block_id] = int(counts.get(block_id) or 0) + 1
        self.record_block_reference(block_id)

    def is_archived(self, block_id: str) -> bool:
        block_id = str(block_id or "").strip()
        if not block_id:
            return False
        archived = set(self._meta().get("archived_block_ids") or [])
        return block_id in archived

    def block_is_active(self, block: dict) -> bool:
        if not isinstance(block, dict):
            return False
        if (block.get("data") or {}).get("archived"):
            return False
        block_id = str(block.get("block_id") or "")
        return not block_id or not self.is_archived(block_id)

    @staticmethod
    def _block_age_seconds(block: dict) -> float:
        data = block.get("data") or {}
        ts = block.get("timestamp") or data.get("timestamp") or data.get("created_at")
        if ts is None:
            return 0.0
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return max(0.0, time.time() - dt.timestamp())
            return max(0.0, time.time() - float(ts))
        except Exception:
            return 0.0

    def _archive_blocks_jsonl(self, blocks: List[dict], tag: str) -> str:
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = self.archive_dir / f"prune-{tag}-{stamp}.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for block in blocks:
                handle.write(json.dumps(block, ensure_ascii=False) + "\n")
        return str(path)

    def _summarize_dispute(self, block_id: str, count: int, blocks: List[dict]) -> dict:
        snippets: List[str] = []
        for block in blocks:
            data = block.get("data") or {}
            text = str(data.get("content") or data.get("response_text") or "")[:160]
            if text:
                snippets.append(text)
        summary = f"Knowledge Conclusion · {block_id[:20]} — disputed {count}×. "
        if snippets:
            summary += "Compressed: " + " | ".join(snippets[:3])[:400]
        return {
            "block_id": f"kc-{block_id[:20]}-{int(time.time())}",
            "label": "knowledge_conclusion",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "content": summary,
                "source_block_id": block_id,
                "conflict_count": count,
                "archived_from": [str(b.get("block_id") or "") for b in blocks],
                "kind": "knowledge_conclusion",
            },
        }

    def run_cycle(self, *, dry_run: bool = False) -> dict:
        report: Dict[str, Any] = {
            "ok": True,
            "dry_run": dry_run,
            "archived_blocks": 0,
            "summaries_created": 0,
            "archive_files": [],
        }
        if not self.enabled:
            report["ok"] = False
            report["error"] = "disabled"
            return report

        meta = self._meta()
        ref_counts = meta.setdefault("ref_counts", {})
        conflict_counts = meta.setdefault("conflict_counts", {})
        archived_set: Set[str] = set(meta.get("archived_block_ids") or [])
        now = time.time()
        summarized_ids: Set[str] = set()

        for block_id, count in list(conflict_counts.items()):
            if count < self.conflict_summary_threshold or block_id in archived_set:
                continue
            related = [
                block
                for block in self.block_store.blocks
                if str(block.get("block_id") or "") == block_id
            ]
            if not related:
                archived_set.add(block_id)
                continue
            if dry_run:
                report["summaries_created"] += 1
                summarized_ids.add(block_id)
                continue
            conclusion = self._summarize_dispute(block_id, count, related)
            self.block_store.add(conclusion)
            meta.setdefault("knowledge_conclusions", []).append(
                {
                    "block_id": conclusion["block_id"],
                    "source_block_id": block_id,
                    "at": now,
                    "conflict_count": count,
                }
            )
            for block in related:
                block.setdefault("data", {})["archived"] = True
                block["data"]["archive_reason"] = "dispute_summarized"
            archived_set.add(block_id)
            summarized_ids.add(block_id)
            report["summaries_created"] += 1
            self.block_store.blocks = [
                block
                for block in self.block_store.blocks
                if str(block.get("block_id") or "") != block_id
            ]
            if self.audit_fn:
                self.audit_fn(
                    "cognitive.prune.summarize",
                    {"block_id": block_id, "conclusion_id": conclusion["block_id"], "count": count},
                )
            if report["summaries_created"] >= 5:
                break

        cold_candidates: List[dict] = []
        for block in self.block_store.blocks:
            block_id = str(block.get("block_id") or "")
            label = str(block.get("label") or (block.get("data") or {}).get("label") or "")
            if not block_id or block_id in archived_set or block_id in summarized_ids:
                continue
            if label in self.PROTECT_LABELS:
                continue
            if (block.get("data") or {}).get("archived"):
                continue
            if int(ref_counts.get(block_id) or 0) > 0:
                continue
            if self._block_age_seconds(block) < self.cold_min_age:
                continue
            cold_candidates.append(block)

        batch = cold_candidates[: self.max_archive_per_run]
        if batch:
            if dry_run:
                report["archived_blocks"] = len(batch)
            else:
                path = self._archive_blocks_jsonl(batch, "cold")
                report["archive_files"].append(path)
                remove_ids = {str(block.get("block_id") or "") for block in batch}
                for block_id in remove_ids:
                    archived_set.add(block_id)
                self.block_store.blocks = [
                    block
                    for block in self.block_store.blocks
                    if str(block.get("block_id") or "") not in remove_ids
                ]
                report["archived_blocks"] = len(batch)
                if self.audit_fn:
                    self.audit_fn(
                        "cognitive.prune.archive",
                        {"count": len(batch), "path": path},
                    )

        meta["archived_block_ids"] = sorted(archived_set)
        meta["total_archived"] = int(meta.get("total_archived") or 0) + int(report["archived_blocks"])
        meta["total_summarized"] = int(meta.get("total_summarized") or 0) + int(report["summaries_created"])
        meta["last_run_at"] = now
        meta["last_report"] = report
        return report

    def status(self) -> dict:
        meta = self._meta()
        active = sum(1 for block in self.block_store.blocks if self.block_is_active(block))
        return {
            "enabled": self.enabled,
            "cold_min_age_seconds": self.cold_min_age,
            "conflict_summary_threshold": self.conflict_summary_threshold,
            "active_blocks": active,
            "archived_block_ids": len(meta.get("archived_block_ids") or []),
            "knowledge_conclusions": len(meta.get("knowledge_conclusions") or []),
            "ref_tracked": len(meta.get("ref_counts") or {}),
            "dispute_tracked": len(meta.get("conflict_counts") or {}),
            "last_run_at": meta.get("last_run_at"),
            "total_archived": meta.get("total_archived", 0),
            "total_summarized": meta.get("total_summarized", 0),
            "last_report": meta.get("last_report"),
        }
