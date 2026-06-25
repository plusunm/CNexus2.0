"""Emergent / reflection converse audit events."""

from __future__ import annotations

from typing import Dict

from .audit_emitter import AuditEmitter


class ConverseAuditService:
    """Records emergent thinking audit rows — no app_v2 imports."""

    def __init__(self, audit: AuditEmitter, *, reply_preview_chars: int = 480):
        self._audit = audit
        self._reply_preview_chars = reply_preview_chars

    def audit_thinking(self, profile: dict, trace_id: str, reply: str) -> None:
        if not profile.get("use_reflection"):
            return
        self._audit.event(
            "converse.emergent",
            {
                "trace_id": trace_id,
                "thinking_mode": profile.get("thinking_mode"),
                "global_entropy": profile.get("global_entropy"),
                "temperature": profile.get("temperature"),
                "reply_preview": str(reply or "")[: self._reply_preview_chars],
            },
        )
