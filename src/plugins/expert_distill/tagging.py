"""Expert block tagging — subject + semantic dimension metadata."""

from __future__ import annotations

from typing import Any, Dict, Optional


def stamp_expert_metadata(
    block: Dict[str, Any],
    *,
    subject_id: str,
    semantic_dimension: str,
    distill_mode: Optional[str] = None,
    plugin: str = "expert_distill",
) -> Dict[str, Any]:
    out = dict(block)
    data = dict(out.get("data") or {})
    sid = str(subject_id or "").strip()
    if sid:
        data["subject_id"] = sid
        data["expert_id"] = sid
    dim = str(semantic_dimension or "fact").strip().lower()
    data["semantic_dimension"] = dim
    data["distill_mode"] = str(distill_mode or dim)
    data["plugin"] = plugin
    data.setdefault("fact_confirm_required", False)
    data.setdefault("fact_confirmed", False)
    out["data"] = data
    return out
