"""P5.3 — Execution gate: plan → policy check → ALLOW / DENY / REQUIRE_CONFIRM."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    from protocol.constants import (
        EXECUTION_GATE_ALLOW,
        EXECUTION_GATE_DENY,
        EXECUTION_GATE_REQUIRE_CONFIRM,
    )
    from protocol.models import ExecutionPolicy, RepairPlan
except ImportError:
    from cnexus_protocol.constants import (
        EXECUTION_GATE_ALLOW,
        EXECUTION_GATE_DENY,
        EXECUTION_GATE_REQUIRE_CONFIRM,
    )
    from cnexus_protocol.models import ExecutionPolicy, RepairPlan


def _normalize_host(host: str) -> str:
    value = str(host or "").strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = "http://" + value
    return value.lower()


def build_source_catalog(suggested_sources: Optional[Sequence[Mapping[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}
    for row in suggested_sources or []:
        if not isinstance(row, dict):
            continue
        host = _normalize_host(str(row.get("host") or ""))
        if host:
            catalog[host] = dict(row)
    return catalog


def _probe_allows_chunk(source_row: Dict[str, Any], chunk_hash: str) -> Tuple[bool, str]:
    probe = source_row.get("probe") if isinstance(source_row.get("probe"), dict) else {}
    if not probe.get("state_checked"):
        return False, "probe_not_checked"
    for state in probe.get("chunk_states") or []:
        if not isinstance(state, dict):
            continue
        if str(state.get("hash") or "").lower() == str(chunk_hash or "").lower():
            if state.get("remote_has"):
                return True, "probe_remote_has"
            return False, "probe_remote_missing"
    if probe.get("remote_has"):
        return True, "probe_remote_has_all"
    if probe.get("remote_has_partial"):
        return False, "probe_partial_only"
    return False, "probe_no_evidence"


def check_plan(
    plan: RepairPlan,
    policy: ExecutionPolicy,
    *,
    source_catalog: Mapping[str, Dict[str, Any]],
    user_confirmed: bool = False,
) -> Dict[str, Any]:
    """Evaluate one repair plan against execution policy and probe evidence."""
    source_checks: List[Dict[str, Any]] = []
    allowed_source_found = False

    for source in plan.sources:
        host = _normalize_host(source)
        row = source_catalog.get(host, {})
        reason = str(row.get("reason") or "unknown")
        check: Dict[str, Any] = {
            "source": source,
            "reason": reason,
            "gate": EXECUTION_GATE_DENY,
            "detail": "",
        }

        if reason not in policy.allowed_sources:
            check["detail"] = f"source_reason_not_allowed:{reason}"
            source_checks.append(check)
            continue

        if policy.require_probe:
            ok, detail = _probe_allows_chunk(row, plan.chunk_hash)
            if not ok:
                check["detail"] = detail
                source_checks.append(check)
                continue

        check["gate"] = EXECUTION_GATE_ALLOW
        check["detail"] = "policy_and_probe_pass"
        allowed_source_found = True
        source_checks.append(check)
        break

    if not allowed_source_found:
        return {
            "chunk_hash": plan.chunk_hash,
            "gate": EXECUTION_GATE_DENY,
            "sources": source_checks,
            "detail": "no_permitted_source",
        }

    if policy.require_user_confirm and not user_confirmed:
        return {
            "chunk_hash": plan.chunk_hash,
            "gate": EXECUTION_GATE_REQUIRE_CONFIRM,
            "sources": source_checks,
            "detail": "user_confirm_required",
        }

    return {
        "chunk_hash": plan.chunk_hash,
        "gate": EXECUTION_GATE_ALLOW,
        "sources": source_checks,
        "detail": "execution_permitted",
    }


def evaluate_execution_gate(
    plans: Sequence[RepairPlan],
    policy: ExecutionPolicy,
    *,
    suggested_sources: Optional[Sequence[Mapping[str, Any]]] = None,
    user_confirmed: bool = False,
) -> Dict[str, Any]:
    """Batch gate evaluation — mandatory filter before execute."""
    catalog = build_source_catalog(suggested_sources)
    decisions = [check_plan(plan, policy, source_catalog=catalog, user_confirmed=user_confirmed) for plan in plans]

    allow_hashes = [d["chunk_hash"] for d in decisions if d["gate"] == EXECUTION_GATE_ALLOW]
    deny_hashes = [d["chunk_hash"] for d in decisions if d["gate"] == EXECUTION_GATE_DENY]
    confirm_hashes = [d["chunk_hash"] for d in decisions if d["gate"] == EXECUTION_GATE_REQUIRE_CONFIRM]

    if confirm_hashes:
        overall = EXECUTION_GATE_REQUIRE_CONFIRM
    elif allow_hashes:
        overall = EXECUTION_GATE_ALLOW
    else:
        overall = EXECUTION_GATE_DENY

    allowed_plans = [plan for plan in plans if plan.chunk_hash in allow_hashes]

    return {
        "ok": overall == EXECUTION_GATE_ALLOW,
        "gate": overall,
        "policy": policy.to_dict(),
        "user_confirmed": bool(user_confirmed),
        "decisions": decisions,
        "allowed_count": len(allowed_plans),
        "denied_count": len(deny_hashes),
        "confirm_required_count": len(confirm_hashes),
        "allowed_plans": [p.to_dict() for p in allowed_plans],
    }
