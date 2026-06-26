"""P5.1 — Repair plan generator (intent layer, not execution)."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    from protocol.constants import REPAIR_STRATEGY_PULL_VERIFY_STORE
    from protocol.models import MissingDiff, RepairPlan
except ImportError:
    from cnexus_protocol.constants import REPAIR_STRATEGY_PULL_VERIFY_STORE
    from cnexus_protocol.models import MissingDiff, RepairPlan


def build_repair_plans(
    diff: MissingDiff,
    *,
    sources: Optional[Sequence[str]] = None,
    graph_importance: float = 1.0,
    commit_recency: float = 0.0,
    head_generation: int = 1,
) -> List[RepairPlan]:
    """
    Generate repair intents for missing + invalid chunks.
    Priority = graph importance + commit recency + head generation weight.
    """
    src = tuple(str(s).strip() for s in (sources or ()) if str(s).strip())
    targets = list(diff.missing) + list(diff.invalid)
    if not targets:
        return []

    recency = float(commit_recency or time.time())
    age_hours = max(0.0, (time.time() - recency) / 3600.0)
    recency_score = max(0.0, 100.0 - age_hours)

    plans: List[RepairPlan] = []
    for chunk_hash in targets:
        priority = (
            float(graph_importance) * 10.0
            + recency_score * 0.1
            + float(head_generation) * 0.5
        )
        plans.append(
            RepairPlan(
                chunk_hash=chunk_hash,
                priority=round(priority, 4),
                sources=src,
                strategy=REPAIR_STRATEGY_PULL_VERIFY_STORE,
                root_hash=diff.root_hash,
                graph_id=diff.graph_id,
                commit_id=diff.commit_id,
            )
        )
    plans.sort(key=lambda p: p.priority, reverse=True)
    return plans


def plans_from_diff_rows(
    diffs: Iterable[MissingDiff],
    *,
    sources: Optional[Sequence[str]] = None,
    catalog_hints: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[RepairPlan]:
    """Build plans for multiple manifest diffs with optional catalog metadata."""
    all_plans: List[RepairPlan] = []
    hints = catalog_hints or {}
    for diff in diffs:
        hint = hints.get(diff.graph_id) or hints.get(diff.root_hash) or {}
        all_plans.extend(
            build_repair_plans(
                diff,
                sources=sources,
                graph_importance=float(hint.get("importance") or 1.0),
                commit_recency=float(hint.get("updated_at") or 0.0),
                head_generation=int(hint.get("head_generation") or 1),
            )
        )
    all_plans.sort(key=lambda p: p.priority, reverse=True)
    return all_plans
