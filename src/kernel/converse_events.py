"""Converse stream event contract (kernel-owned, gateway adapts to SSE)."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, NotRequired, Optional, TypedDict


class ConverseEventType(str, Enum):
    META = "meta"
    STATUS = "status"
    CHUNK = "chunk"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    DONE = "done"


class ConverseEvent(TypedDict):
    event: ConverseEventType
    data: Any
    step: NotRequired[Optional[str]]
    causality_id: NotRequired[Optional[str]]


def converse_event(
    event: ConverseEventType,
    data: Any,
    *,
    step: Optional[str] = None,
    causality_id: Optional[str] = None,
) -> ConverseEvent:
    out: ConverseEvent = {"event": event, "data": data}
    if step is not None:
        out["step"] = step
    if causality_id is not None:
        out["causality_id"] = causality_id
    return out


def legacy_sse_event_name(event: ConverseEvent) -> str:
    kind = event["event"]
    if kind == ConverseEventType.CHUNK:
        return "token"
    if kind == ConverseEventType.META:
        return "meta"
    return kind.value


def legacy_sse_payload(event: ConverseEvent) -> Dict[str, Any]:
    kind = event["event"]
    data = event["data"]
    if kind == ConverseEventType.CHUNK:
        payload: Dict[str, Any] = {"text": data}
    elif kind == ConverseEventType.ERROR:
        payload = data if isinstance(data, dict) else {"error": str(data)}
    elif kind == ConverseEventType.DONE:
        payload = data if isinstance(data, dict) else {"ok": True, "reply": str(data)}
    elif kind == ConverseEventType.STATUS:
        payload = {"status": str(data)}
    elif isinstance(data, dict):
        payload = dict(data)
    else:
        payload = {"value": data}
    step = event.get("step")
    if step:
        payload["step"] = step
    causality_id = event.get("causality_id")
    if causality_id:
        payload["causality_id"] = causality_id
    return payload


def event_to_sse_string(event: ConverseEvent) -> str:
    name = legacy_sse_event_name(event)
    payload = legacy_sse_payload(event)
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
