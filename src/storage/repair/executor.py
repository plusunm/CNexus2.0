"""P5.2 — Controlled repair executor (deterministic, bounded)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence

try:
    from protocol.constants import REPAIR_POLICY_DETERMINISTIC, REPAIR_STRATEGY_PULL_VERIFY_STORE
    from protocol.models import RepairPlan
except ImportError:
    from cnexus_protocol.constants import REPAIR_POLICY_DETERMINISTIC, REPAIR_STRATEGY_PULL_VERIFY_STORE
    from cnexus_protocol.models import RepairPlan

from ..service import StorageService


def execute_repair_plans(
    storage: StorageService,
    plans: Sequence[RepairPlan],
    *,
    verifier_peer_id: str = "",
    max_concurrent: int = 2,
    max_plans: int = 32,
) -> Dict[str, Any]:
    """
    Execute repair intents via P4.5 pull — no gossip, no autonomous sync.
    Repair is deterministic: only explicit plans are executed.
    """
    if max_concurrent < 1:
        max_concurrent = 1
    ordered = sorted(plans, key=lambda p: p.priority, reverse=True)[: max(0, int(max_plans))]
    if not ordered:
        return {"ok": True, "policy": REPAIR_POLICY_DETERMINISTIC, "executed": 0, "results": []}

    results: List[Dict[str, Any]] = []

    def _run(plan: RepairPlan) -> Dict[str, Any]:
        if plan.strategy != REPAIR_STRATEGY_PULL_VERIFY_STORE:
            return {
                "ok": False,
                "hash": plan.chunk_hash,
                "error": f"unsupported_strategy:{plan.strategy}",
            }
        if not plan.sources:
            return {"ok": False, "hash": plan.chunk_hash, "error": "missing_sources"}
        last: Dict[str, Any] = {"ok": False, "hash": plan.chunk_hash}
        for source in plan.sources:
            report = storage.pull_chunk_from_peer(
                source,
                plan.chunk_hash,
                verifier_peer_id=verifier_peer_id,
            )
            last = dict(report)
            last["source"] = source
            last["priority"] = plan.priority
            if report.get("ok"):
                return last
        return last

    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        futures = {pool.submit(_run, plan): plan for plan in ordered}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                plan = futures[future]
                results.append({"ok": False, "hash": plan.chunk_hash, "error": str(exc)})

    ok_count = sum(1 for row in results if row.get("ok"))
    return {
        "ok": ok_count == len(results) and len(results) > 0,
        "policy": REPAIR_POLICY_DETERMINISTIC,
        "executed": len(results),
        "repaired": ok_count,
        "results": results,
    }
