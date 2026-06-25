"""Shared audit event emitter for converse turn + emergent audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

AuditEventFn = Callable[[str, Dict[str, Any]], Any]


@dataclass(frozen=True)
class AuditEmitterHooks:
    audit_event: AuditEventFn


class AuditEmitter:
    def __init__(self, hooks: AuditEmitterHooks):
        self._hooks = hooks

    def event(self, kind: str, payload: Dict[str, Any]) -> None:
        self._hooks.audit_event(kind, payload)
