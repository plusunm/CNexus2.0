"""Boot-time share policy — publish local memory blocks to cognitive/catalog."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

try:
    from protocol.ids import graph_id_for_owner_topic
except ImportError:
    from cnexus_protocol.ids import graph_id_for_owner_topic


def share_local_memory_enabled() -> bool:
    return os.environ.get("CNEXUS_SHARE_LOCAL_MEMORY", "1").lower() not in ("0", "false", "no")


def share_local_memory_always() -> bool:
    return os.environ.get("CNEXUS_SHARE_LOCAL_MEMORY_ALWAYS", "1").lower() not in ("0", "false", "no")


def bootstrap_share_local_memory(
    app: Any,
    *,
    memory_blocks: List[Dict[str, Any]],
    identity_pubkey: str = "",
    topic: str = "memory/local",
) -> Dict[str, Any]:
    """
    Publish local BlockStore rows to catalog on startup (default ON).
    Skips when no blocks, no identity, or graph already has a head (unless ALWAYS=1, default ON).
    """
    if not share_local_memory_enabled():
        return {"ok": True, "skipped": True, "reason": "disabled"}
    if app is None:
        return {"ok": False, "skipped": True, "reason": "application_unavailable"}
    if not memory_blocks:
        return {"ok": True, "skipped": True, "reason": "no_blocks"}

    owner = str(identity_pubkey or "").strip().lower()
    if not owner:
        return {"ok": False, "skipped": True, "reason": "identity_unavailable"}

    graph_id = graph_id_for_owner_topic(owner, topic)
    if not share_local_memory_always():
        cognitive = getattr(app, "cognitive", None)
        store = getattr(cognitive, "store", None) if cognitive else None
        if store is not None:
            head = store.get_head_commit_id(graph_id)
            if head:
                return {
                    "ok": True,
                    "skipped": True,
                    "reason": "already_published",
                    "graph_id": graph_id,
                    "head_commit": head,
                }

    try:
        result = app.publish_memory(topic=topic)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "graph_id": graph_id}

    if not result.get("ok"):
        return {"ok": False, **result, "graph_id": graph_id}

    report = {
        "ok": True,
        "shared": True,
        "graph_id": result.get("graph_id") or graph_id,
        "commit_id": result.get("commit_id"),
        "root_hash": result.get("root_hash"),
        "block_count": len(memory_blocks),
    }
    _maybe_register_share_stats(report)
    return report


def _maybe_register_share_stats(report: Dict[str, Any]) -> None:
    data_dir = str(os.environ.get("CNEXUS_DATA_DIR") or os.path.join(os.getcwd(), "data"))
    version = str(os.environ.get("CNEXUS_VERSION") or "2.4.0")
    edition = str(os.environ.get("CNEXUS_EDITION") or "personal")
    try:
        try:
            from core.share_stats import try_register_share
        except ImportError:
            from share_stats import try_register_share  # type: ignore
        try_register_share(
            data_dir,
            graph_id=str(report.get("graph_id") or ""),
            block_count=int(report.get("block_count") or 0),
            commit_id=str(report.get("commit_id") or ""),
            root_hash=str(report.get("root_hash") or ""),
            version=version,
            edition=edition,
        )
    except Exception:
        pass
