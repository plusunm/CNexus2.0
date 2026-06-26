"""L1 Conversation Scratch — ephemeral session context, not Foundation."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

MutateEngineFn = Callable[[Callable[[Dict[str, Any]], Any]], Any]

DEFAULT_MAX_ITEMS = 24
DEFAULT_TTL_SECONDS = 4 * 3600


def default_scratch_state() -> Dict[str, Any]:
    return {
        "session_id": "",
        "items": [],
        "updated_at": 0.0,
        "expires_at": 0.0,
    }


def normalize_scratch(engine: Dict[str, Any]) -> Dict[str, Any]:
    scratch = dict(engine.get("conversation_scratch") or default_scratch_state())
    scratch.setdefault("items", [])
    return scratch


def prune_scratch(scratch: Dict[str, Any], *, now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else float(now)
    expires = float(scratch.get("expires_at") or 0)
    if expires and now > expires:
        return default_scratch_state()
    items = list(scratch.get("items") or [])
    if len(items) > DEFAULT_MAX_ITEMS:
        items = items[-DEFAULT_MAX_ITEMS:]
    scratch["items"] = items
    return scratch


def append_scratch_turn(
    mutate_engine: MutateEngineFn,
    *,
    session_id: str,
    user_text: str,
    assistant_text: str,
    trace_id: str = "",
) -> Dict[str, Any]:
    now = time.time()

    def apply(engine: Dict[str, Any]) -> Dict[str, Any]:
        scratch = prune_scratch(normalize_scratch(engine), now=now)
        sid = str(session_id or scratch.get("session_id") or f"session-{int(now * 1000)}")
        if scratch.get("session_id") and scratch.get("session_id") != sid:
            scratch = default_scratch_state()
            scratch["session_id"] = sid
        if not scratch.get("session_id"):
            scratch["session_id"] = sid
        items: List[Dict[str, Any]] = list(scratch.get("items") or [])
        user = str(user_text or "").strip()
        assistant = str(assistant_text or "").strip()
        if user:
            items.append({"role": "user", "text": user[:800], "trace_id": trace_id, "ts": now})
        if assistant:
            items.append({"role": "assistant", "text": assistant[:1200], "trace_id": trace_id, "ts": now})
        scratch["items"] = items[-DEFAULT_MAX_ITEMS:]
        scratch["updated_at"] = now
        scratch["expires_at"] = now + DEFAULT_TTL_SECONDS
        engine["conversation_scratch"] = scratch
        return {"ok": True, "count": len(scratch["items"]), "session_id": sid}

    return mutate_engine(apply)


def clear_scratch(mutate_engine: MutateEngineFn) -> Dict[str, Any]:
    def apply(engine: Dict[str, Any]) -> Dict[str, Any]:
        engine["conversation_scratch"] = default_scratch_state()
        return {"ok": True, "cleared": True}

    return mutate_engine(apply)


def format_scratch_for_prompt(scratch: Dict[str, Any], *, max_items: int = 8) -> str:
    scratch = prune_scratch(scratch)
    items = list(scratch.get("items") or [])[-max_items:]
    if not items:
        return ""
    lines = [
        "--- L1 Conversation Scratch (ephemeral · session-local) ---",
        f"session={scratch.get('session_id') or 'anonymous'}",
    ]
    for item in items:
        role = str(item.get("role") or "user")
        text = str(item.get("text") or "").strip()
        if text:
            lines.append(f"[{role}] {text[:400]}")
    return "\n".join(lines)


def scratch_status(engine: Dict[str, Any]) -> Dict[str, Any]:
    scratch = prune_scratch(normalize_scratch(engine))
    return {
        "ok": True,
        "session_id": scratch.get("session_id") or "",
        "item_count": len(scratch.get("items") or []),
        "updated_at": scratch.get("updated_at") or 0,
        "expires_at": scratch.get("expires_at") or 0,
    }
