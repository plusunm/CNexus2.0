"""Commit DAG utilities — ancestry walk and pull ordering."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set

try:
    from protocol.models import Commit
except ImportError:
    from cnexus_protocol.models import Commit


GetCommitFn = Callable[[str], Optional[Commit]]


def collect_ancestors(commit_id: str, get_commit: GetCommitFn, *, limit: int = 4096) -> List[str]:
    """Return commit_ids from head toward root (head first)."""
    order: List[str] = []
    seen: Set[str] = set()
    stack = [str(commit_id or "")]
    while stack and len(order) < limit:
        cid = stack.pop()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        row = get_commit(cid)
        if row is None:
            order.append(cid)
            continue
        order.append(row.commit_id)
        for parent in reversed(row.parent_ids):
            if parent and parent not in seen:
                stack.append(parent)
    return order


def commits_since(
    head_commit_id: str,
    since_commit_id: str,
    get_commit: GetCommitFn,
    *,
    limit: int = 256,
) -> List[Commit]:
    """
    Commits on path from head back toward root, excluding since and its ancestors.
    Returns oldest-first (safe apply order).
    """
    chain = collect_ancestors(head_commit_id, get_commit, limit=limit)
    if not since_commit_id:
        rows = []
        for cid in reversed(chain):
            row = get_commit(cid)
            if row:
                rows.append(row)
        return rows

    since = since_commit_id.strip().lower()
    if since not in {c.lower() for c in chain}:
        # Diverged history — return full chain for caller to merge
        rows = []
        for cid in reversed(chain):
            row = get_commit(cid)
            if row:
                rows.append(row)
        return rows

    trimmed: List[str] = []
    for cid in chain:
        if cid.lower() == since:
            break
        trimmed.append(cid)
    rows = []
    for cid in reversed(trimmed):
        row = get_commit(cid)
        if row:
            rows.append(row)
    return rows


def dag_payload(graph_id: str, head_commit_id: str, get_commit: GetCommitFn, *, limit: int = 512) -> List[dict]:
    """Serialize commit DAG from head for API responses."""
    chain = collect_ancestors(head_commit_id, get_commit, limit=limit)
    nodes: List[dict] = []
    for cid in reversed(chain):
        row = get_commit(cid)
        if row and row.graph_id == graph_id:
            nodes.append(row.to_dict())
    return nodes
