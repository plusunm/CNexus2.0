"""Bridge audit-chain negotiation failures to ConflictResolutionAgent."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.conflict_resolution import normalize_content


def memory_rows_from_audit_entries(entries: list) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for entry in entries or []:
        data = dict(entry.get("data") or {})
        if str(data.get("event") or "") != "memory.block":
            continue
        block_id = str(data.get("block_id") or "").strip()
        if not block_id:
            continue
        rows[block_id] = {
            "block_id": block_id,
            "label": str(data.get("label") or "episode"),
            "content": str(data.get("content_preview") or data.get("content") or ""),
            "source_peer": str(data.get("source_peer") or ""),
        }
    return rows


def find_memory_block_conflicts(
    local_entries: list,
    remote_entries: list,
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    local_rows = memory_rows_from_audit_entries(local_entries)
    remote_rows = memory_rows_from_audit_entries(remote_entries)
    conflicts: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for block_id, local_row in local_rows.items():
        remote_row = remote_rows.get(block_id)
        if not remote_row:
            continue
        if normalize_content(local_row.get("content")) != normalize_content(remote_row.get("content")):
            conflicts.append((dict(local_row), dict(remote_row)))
    return conflicts


def format_resolution_snippet(resolution: dict) -> str:
    status = str(resolution.get("status") or "")
    if status == "merged":
        text = str(resolution.get("merged_content") or "").strip()
        return f"[merged] {text[:320]}"
    if status == "forked":
        fork = dict(resolution.get("fork") or {})
        return (
            f"[forked] local: {str(fork.get('local') or '')[:160]} | "
            f"remote: {str(fork.get('remote') or '')[:160]}"
        )
    if status == "aligned":
        return f"[aligned] {str(resolution.get('merged_content') or '')[:160]}"
    return f"[{status}] {str(resolution.get('rationale') or '')[:160]}"


def format_negotiation_conflict_context(buffer: list, *, limit: int = 3) -> str:
    if not buffer:
        return ""
    lines = ["--- Recent negotiation conflicts (cross-node synthesis) ---"]
    shown = 0
    for item in buffer[:limit]:
        peer = str(item.get("peer_pubkey") or "peer")[:16]
        err = str(item.get("negotiation_error") or "negotiation_failed")
        entropy = str(item.get("global_entropy") or "")
        if entropy:
            lines.append(f"Peer {peer} · {err} · entropy {entropy}")
        else:
            lines.append(f"Peer {peer} · {err}")
        for resolution in item.get("resolutions") or []:
            lines.append(format_resolution_snippet(resolution))
            shown += 1
            if shown >= limit * 2:
                break
        if shown >= limit * 2:
            break
    return "\n".join(lines) if len(lines) > 1 else ""
