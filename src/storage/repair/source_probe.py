"""P5.2 — Source probe enrichment (state-only, no pull, no execution)."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from ..chunk_exchange_client import fetch_chunk_state

PROBE_CHECK_METHOD = "chunk/state"
PROBE_CONFIDENCE = "deterministic"
DEFAULT_PROBE_LIMIT = 32
DEFAULT_PROBE_TIMEOUT = 4.0


def probe_chunk_state(host: str, chunk_hash: str, *, timeout: float = DEFAULT_PROBE_TIMEOUT) -> Dict[str, Any]:
    """
    Existence probe only — GET /api/storage/chunk/state.
    state check ≠ data access ≠ replication.
    """
    try:
        resp = fetch_chunk_state(host, chunk_hash, timeout=timeout)
        exists = bool(resp.get("exists"))
        return {
            "hash": chunk_hash,
            "remote_has": exists,
            "exists": exists,
            "state_checked": True,
            "check_method": PROBE_CHECK_METHOD,
            "confidence": PROBE_CONFIDENCE,
            "encoding": resp.get("encoding"),
            "verified": resp.get("verified"),
        }
    except Exception as exc:
        return {
            "hash": chunk_hash,
            "remote_has": False,
            "exists": False,
            "state_checked": False,
            "check_method": PROBE_CHECK_METHOD,
            "confidence": PROBE_CONFIDENCE,
            "error": str(exc),
        }


def enrich_source_probe(
    source: Dict[str, Any],
    chunk_hashes: Sequence[str],
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
    limit: int = DEFAULT_PROBE_LIMIT,
) -> Dict[str, Any]:
    """Attach deterministic remote state signals to a suggested source row."""
    row = dict(source)
    host = str(row.get("host") or "").strip()
    targets = [str(h) for h in chunk_hashes if str(h).strip()][: max(0, int(limit))]

    if not host or not targets:
        row["remote_has"] = False
        row["state_checked"] = False
        row["check_method"] = PROBE_CHECK_METHOD
        row["confidence"] = PROBE_CONFIDENCE
        row["probe"] = {
            "state_checked": False,
            "check_method": PROBE_CHECK_METHOD,
            "confidence": PROBE_CONFIDENCE,
            "remote_has": False,
            "reason": "no_host_or_no_missing",
            "chunk_states": [],
        }
        return row

    chunk_states: List[Dict[str, Any]] = []
    has_count = 0
    checked = 0
    for chunk_hash in targets:
        state = probe_chunk_state(host, chunk_hash, timeout=timeout)
        chunk_states.append(state)
        if state.get("state_checked"):
            checked += 1
        if state.get("remote_has"):
            has_count += 1

    remote_has_all = has_count == len(targets) and len(targets) > 0
    row["remote_has"] = remote_has_all
    row["remote_has_partial"] = has_count > 0
    row["state_checked"] = checked == len(targets)
    row["check_method"] = PROBE_CHECK_METHOD
    row["confidence"] = PROBE_CONFIDENCE
    row["probe"] = {
        "state_checked": row["state_checked"],
        "check_method": PROBE_CHECK_METHOD,
        "confidence": PROBE_CONFIDENCE,
        "remote_has": remote_has_all,
        "remote_has_partial": has_count > 0,
        "remote_has_count": has_count,
        "missing_queried": len(targets),
        "chunk_states": chunk_states,
    }
    return row


def enrich_suggested_sources(
    sources: Sequence[Dict[str, Any]],
    chunk_hashes: Sequence[str],
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
    limit: int = DEFAULT_PROBE_LIMIT,
) -> List[Dict[str, Any]]:
    """Probe each suggested source — observability only, no execution."""
    if not chunk_hashes:
        enriched: List[Dict[str, Any]] = []
        for source in sources:
            row = dict(source)
            row["probe"] = {
                "state_checked": False,
                "check_method": PROBE_CHECK_METHOD,
                "confidence": PROBE_CONFIDENCE,
                "remote_has": False,
                "reason": "nothing_to_probe",
                "chunk_states": [],
            }
            enriched.append(row)
        return enriched
    return [
        enrich_source_probe(source, chunk_hashes, timeout=timeout, limit=limit)
        for source in sources
    ]
