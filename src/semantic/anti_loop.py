"""Anti-loop write barrier — SSS-03: LLM output ≠ memory write source."""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Optional


def apply_antiloop_after_store(
    block_store: Any,
    semantic_turn: Optional[Mapping[str, Any]],
    iteration_meta: Optional[MutableMapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tag episodic blocks written during expert sessions for REM exclusion / fact-confirm.
    """
    meta = dict(semantic_turn or {})
    expert_mode = str(meta.get("expert_mode") or "").strip()
    if not expert_mode:
        return {"tagged": False, "reason": "no_expert_mode"}

    if iteration_meta is not None:
        iteration_meta["expert_session"] = True
        iteration_meta["expert_mode"] = expert_mode
        iteration_meta["fact_confirm_required"] = True

    blocks = getattr(block_store, "blocks", None)
    if not isinstance(blocks, list):
        return {"tagged": False, "reason": "no_block_store"}

    tagged = 0
    for block in reversed(blocks):
        if str(block.get("label") or "") != "episodic":
            continue
        data = dict(block.get("data") or {})
        if data.get("derived_from_expert_session"):
            break
        data["derived_from_expert_session"] = True
        data["fact_confirm_required"] = True
        data["expert_mode"] = expert_mode
        data["write_provenance"] = "llm-output-session"
        data.setdefault("semantic_dimension", "episodic")
        block["data"] = data
        tagged = 1
        break

    return {"tagged": tagged > 0, "expert_mode": expert_mode}


def should_skip_rem_for_block(block: Mapping[str, Any]) -> bool:
    """REM synthesis should not distill style from expert-session episodic rows."""
    data = dict(block.get("data") or {})
    if data.get("fact_confirmed"):
        return False
    if data.get("derived_from_expert_session"):
        return True
    if str(data.get("write_provenance") or "") == "llm-output-session":
        return True
    dim = str(data.get("semantic_dimension") or "")
    if dim in ("style", "persona_summary") and not data.get("fact_confirmed"):
        return True
    return False
