"""Cognitive provenance — honest LLM context for preview / remote fragments."""

from __future__ import annotations

from typing import Any, Dict, Optional

PROVENANCE_LOCAL_FULL = "local-full"
PROVENANCE_AUDIT_PREVIEW = "audit-preview"
PROVENANCE_REMOTE_PREVIEW = "remote-preview"

PREVIEW_CHAR_HINT = 480


def provenance_from_block(block: dict) -> str:
    data = dict((block or {}).get("data") or {})
    explicit = str(data.get("provenance") or "").strip()
    if explicit:
        return explicit
    if str(data.get("source_peer") or "").strip():
        return PROVENANCE_REMOTE_PREVIEW
    if data.get("replayed"):
        return PROVENANCE_AUDIT_PREVIEW
    return PROVENANCE_LOCAL_FULL


def provenance_label(provenance: str) -> str:
    if provenance == PROVENANCE_REMOTE_PREVIEW:
        return "Remote-Preview"
    if provenance == PROVENANCE_AUDIT_PREVIEW:
        return "Audit-Preview"
    return "Local-Full"


def is_preview_provenance(provenance: str) -> bool:
    return provenance in (PROVENANCE_AUDIT_PREVIEW, PROVENANCE_REMOTE_PREVIEW)


def format_llm_memory_fragment(
    content: str,
    *,
    provenance: str,
    source_peer: str = "",
    block_id: str = "",
) -> str:
    text = str(content or "").strip()
    if not text:
        return ""
    if not is_preview_provenance(provenance):
        return text

    tag = provenance_label(provenance)
    peer_line = f"\n[Source: {source_peer}]" if source_peer else ""
    id_line = f"\n[Block: {block_id}]" if block_id else ""
    return (
        f"[Provenance: {tag}]{peer_line}{id_line}\n"
        f"[Note: 本条记忆仅为同步预览片段（约 {PREVIEW_CHAR_HINT} 字以内），"
        f"不可当作完整事实。推理时请降低权重，必要时标注「根据已知片段推测」。]\n"
        f"----------------\n{text}\n----------------"
    )


def preview_tag_prefix(provenance: str) -> str:
    if not is_preview_provenance(provenance):
        return ""
    return f"[{provenance_label(provenance)}] "


def block_data_with_provenance(
    data: dict,
    *,
    provenance: str,
    source_peer: str = "",
    content_kind: Optional[str] = None,
) -> dict:
    row = dict(data or {})
    row["provenance"] = provenance
    if source_peer:
        row["source_peer"] = source_peer
    if content_kind:
        row["content_kind"] = content_kind
    elif is_preview_provenance(provenance):
        row["content_kind"] = "preview"
    else:
        row["content_kind"] = row.get("content_kind") or "full"
    return row


def provenance_system_preamble() -> str:
    return (
        "Provenance honesty: fragments tagged [Audit-Preview] or [Remote-Preview] are "
        "truncated sync excerpts, not full records. Weight them lower; say when inferring "
        "from partial context.\n"
    )
