"""Expert distillation service — fact-confirm, distill, subject registry."""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Sequence

from .distill import ExpertDistillEngine
from .tagging import stamp_expert_metadata

MutateStoreFn = Callable[[Callable[[Any], Any]], Any]


def expert_distill_enabled() -> bool:
    raw = os.environ.get("CNEXUS_EXPERT_DISTILL", "0")
    return str(raw).lower() not in ("0", "false", "no", "")


def fact_confirm_block(block: Mapping[str, Any]) -> Dict[str, Any]:
    """Promote expert-session output to auditable fact (SSS-03)."""
    out = dict(block)
    data = dict(out.get("data") or {})
    data["fact_confirmed"] = True
    data["fact_confirm_required"] = False
    data["derived_from_expert_session"] = False
    data["semantic_dimension"] = "fact"
    data["provenance"] = "local-full"
    data["write_provenance"] = "fact-confirmed"
    out["data"] = data
    out["importance"] = max(float(out.get("importance") or 0.5), 0.85)
    return out


class ExpertDistillService:
    """Hot-plug expert operations — candidate producer + distill + confirm."""

    def __init__(
        self,
        mutate_memory_store: MutateStoreFn,
        get_blocks: Callable[[], List[Mapping[str, Any]]],
        *,
        schedule_persist: Optional[Callable[[], None]] = None,
        distill_engine: Optional[ExpertDistillEngine] = None,
    ):
        self._mutate_store = mutate_memory_store
        self._get_blocks = get_blocks
        self._schedule_persist = schedule_persist
        self._engine = distill_engine or ExpertDistillEngine()

    def list_subjects(self) -> List[Dict[str, Any]]:
        counts: Counter[str] = Counter()
        dims: Dict[str, Counter[str]] = {}
        for block in self._get_blocks():
            data = dict(block.get("data") or {})
            sid = str(data.get("subject_id") or data.get("expert_id") or "").strip()
            if not sid:
                continue
            counts[sid] += 1
            dim = str(data.get("semantic_dimension") or "unknown")
            dims.setdefault(sid, Counter())[dim] += 1
        return [
            {"subject_id": sid, "block_count": counts[sid], "dimensions": dict(dims.get(sid, {}))}
            for sid in sorted(counts.keys())
        ]

    def run_distill(
        self,
        *,
        subject_id: str,
        modes: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        if not expert_distill_enabled():
            return {"ok": False, "error": "expert_distill_disabled"}
        subject = str(subject_id or "").strip()
        if not subject:
            return {"ok": False, "error": "missing subject_id"}
        mode_list = [str(m).lower() for m in (modes or ("fact", "style", "decision"))]
        blocks = self._engine.distill(self._get_blocks(), subject_id=subject, modes=mode_list)

        def apply(store) -> int:
            for block in blocks:
                store.add(block)
            return len(blocks)

        written = self._mutate_store(apply)
        if self._schedule_persist:
            self._schedule_persist()
        return {
            "ok": True,
            "subject_id": subject,
            "modes": mode_list,
            "blocks_written": written,
            "block_ids": [b.get("block_id") for b in blocks],
        }

    def confirm_fact(self, block_id: str) -> Dict[str, Any]:
        bid = str(block_id or "").strip()
        if not bid:
            return {"ok": False, "error": "missing block_id"}

        found = {"ok": False}

        def apply(store) -> None:
            for i, block in enumerate(store.blocks):
                if str(block.get("block_id") or "") != bid:
                    continue
                data = dict(block.get("data") or {})
                if not data.get("derived_from_expert_session") and not data.get("fact_confirm_required"):
                    found["ok"] = False
                    found["error"] = "block_not_eligible"
                    return
                store.blocks[i] = fact_confirm_block(block)
                found["ok"] = True
                return
            found["error"] = "block_not_found"

        self._mutate_store(apply)
        if found.get("ok") and self._schedule_persist:
            self._schedule_persist()
        if not found.get("ok"):
            return {"ok": False, "error": found.get("error", "confirm_failed")}
        return {"ok": True, "block_id": bid, "status": "fact_confirmed"}

    def capture_for_subject(
        self,
        *,
        subject_id: str,
        content: str,
        semantic_dimension: str = "fact",
        layer: str = "semantic",
    ) -> Dict[str, Any]:
        if not expert_distill_enabled():
            return {"ok": False, "error": "expert_distill_disabled"}
        text = str(content or "").strip()
        subject = str(subject_id or "").strip()
        if not subject or not text:
            return {"ok": False, "error": "missing subject_id or content"}

        import time

        mem_id = f"expert-cap-{int(time.time() * 1000)}"
        block = stamp_expert_metadata(
            {
                "label": layer,
                "block_id": mem_id,
                "data": {"content": text[:2000], "filename": f"expert:{subject}"},
                "importance": 0.8,
                "timestamp": time.time(),
            },
            subject_id=subject,
            semantic_dimension=semantic_dimension,
        )

        def apply(store) -> str:
            store.add(block)
            return mem_id

        mid = self._mutate_store(apply)
        if self._schedule_persist:
            self._schedule_persist()
        return {"ok": True, "memory_id": mid, "subject_id": subject, "block_id": mem_id}
