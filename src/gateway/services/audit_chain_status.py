"""Append-only audit chain status for L0 snapshot and dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class AuditChainStatusHooks:
    audit_optional: bool
    audit_log_path: Callable[[], str]
    get_audit_log: Callable[[], Any]
    get_audit_integrity: Callable[[], Dict[str, Any]]


class AuditChainStatusService:
    def __init__(self, hooks: AuditChainStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        audit = self._hooks.get_audit_log()
        integrity = self._hooks.get_audit_integrity()
        if audit is None:
            return {
                "enabled": not self._hooks.audit_optional,
                "loaded": False,
                "path": self._hooks.audit_log_path(),
                "integrity": integrity,
            }
        last_hash = audit.last_hash
        return {
            "enabled": True,
            "loaded": True,
            "path": self._hooks.audit_log_path(),
            "entries": audit.entry_count(),
            "last_hash": last_hash[:16] + "…" if last_hash != "0" else "0",
            "integrity": integrity,
        }
