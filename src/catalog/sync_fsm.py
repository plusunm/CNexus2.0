"""Catalog sync state machine — generation → summary → bloom → interest → index."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class CatalogSyncPhase(str, Enum):
    INIT = "init"
    GENERATION_CHECK = "generation_check"
    GENERATION_SKIP = "generation_skip"
    SUMMARY_CHECK = "summary_check"
    SUMMARY_SKIP = "summary_skip"
    BLOOM_EXCHANGE = "bloom_exchange"
    INTEREST_FILTER = "interest_filter"
    INDEX_EXCHANGE = "index_exchange"
    COMPLETE = "complete"
    NEED_P3 = "need_p3"
    ERROR = "error"


def build_sync_report(**fields: Any) -> Dict[str, Any]:
    report: Dict[str, Any] = {"ok": False, "phases": []}
    report.update(fields)
    return report


def append_phase(report: Dict[str, Any], phase: CatalogSyncPhase, **detail: Any) -> None:
    phases = list(report.get("phases") or [])
    row = {"phase": phase.value, **detail}
    phases.append(row)
    report["phases"] = phases
    report["phase"] = phase.value
