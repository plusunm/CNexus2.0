"""ProvenancePort — Memory Domain provenance boundary (no app_v2 / core imports)."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

PROVENANCE_LOCAL_FULL = "local-full"
PROVENANCE_AUDIT_PREVIEW = "audit-preview"
PROVENANCE_REMOTE_PREVIEW = "remote-preview"
PREVIEW_CHAR_HINT = 480


def _provenance_label(provenance: str) -> str:
    if provenance == PROVENANCE_REMOTE_PREVIEW:
        return "Remote-Preview"
    if provenance == PROVENANCE_AUDIT_PREVIEW:
        return "Audit-Preview"
    return "Local-Full"


def _is_preview_provenance(provenance: str) -> bool:
    return provenance in (PROVENANCE_AUDIT_PREVIEW, PROVENANCE_REMOTE_PREVIEW)


@runtime_checkable
class ProvenancePort(Protocol):
    """Unified provenance API for recall, context assembly, and LLM preamble."""

    PROVENANCE_AUDIT_PREVIEW: str
    PROVENANCE_LOCAL_FULL: str
    PROVENANCE_REMOTE_PREVIEW: str

    def from_block(self, block: dict) -> str:
        """Resolve provenance tag from a memory block."""

    def format_fragment(
        self,
        content: str,
        *,
        provenance: str,
        source_peer: str = "",
        block_id: str = "",
    ) -> str:
        """Apply preview honesty wrapping for LLM injection."""

    def is_preview(self, provenance: str) -> bool:
        """Whether the tag denotes a truncated sync excerpt."""

    def preview_tag(self, provenance: str) -> str:
        """Short prefix for node-spec descriptions."""

    def build_preamble(self) -> str:
        """System-level provenance honesty preamble for precision mode."""


class DefaultProvenancePort:
    """Self-contained provenance implementation."""

    PROVENANCE_LOCAL_FULL = PROVENANCE_LOCAL_FULL
    PROVENANCE_AUDIT_PREVIEW = PROVENANCE_AUDIT_PREVIEW
    PROVENANCE_REMOTE_PREVIEW = PROVENANCE_REMOTE_PREVIEW

    def from_block(self, block: dict) -> str:
        data = dict((block or {}).get("data") or {})
        explicit = str(data.get("provenance") or "").strip()
        if explicit:
            return explicit
        if str(data.get("source_peer") or "").strip():
            return PROVENANCE_REMOTE_PREVIEW
        if data.get("replayed"):
            return PROVENANCE_AUDIT_PREVIEW
        return PROVENANCE_LOCAL_FULL

    def format_fragment(
        self,
        content: str,
        *,
        provenance: str,
        source_peer: str = "",
        block_id: str = "",
    ) -> str:
        text = str(content or "").strip()
        if not text:
            return ""
        if not _is_preview_provenance(provenance):
            return text

        tag = _provenance_label(provenance)
        peer_line = f"\n[Source: {source_peer}]" if source_peer else ""
        id_line = f"\n[Block: {block_id}]" if block_id else ""
        return (
            f"[Provenance: {tag}]{peer_line}{id_line}\n"
            f"[Note: 本条记忆仅为同步预览片段（约 {PREVIEW_CHAR_HINT} 字以内），"
            f"不可当作完整事实。推理时请降低权重，必要时标注「根据已知片段推测」。]\n"
            f"----------------\n{text}\n----------------"
        )

    def is_preview(self, provenance: str) -> bool:
        return _is_preview_provenance(provenance)

    def preview_tag(self, provenance: str) -> str:
        if not _is_preview_provenance(provenance):
            return ""
        return f"[{_provenance_label(provenance)}] "

    def build_preamble(self) -> str:
        return (
            "Provenance honesty: fragments tagged [Audit-Preview] or [Remote-Preview] are "
            "truncated sync excerpts, not full records. Weight them lower; say when inferring "
            "from partial context.\n"
        )

    def block_data_with_provenance(
        self,
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
        elif _is_preview_provenance(provenance):
            row["content_kind"] = "preview"
        else:
            row["content_kind"] = row.get("content_kind") or "full"
        return row

    # Legacy aliases — core.provenance module and older gateway call sites.
    def provenance_from_block(self, block: dict) -> str:
        return self.from_block(block)

    def format_llm_memory_fragment(
        self,
        content: str,
        *,
        provenance: str,
        source_peer: str = "",
        block_id: str = "",
    ) -> str:
        return self.format_fragment(
            content,
            provenance=provenance,
            source_peer=source_peer,
            block_id=block_id,
        )

    def is_preview_provenance(self, provenance: str) -> bool:
        return self.is_preview(provenance)

    def preview_tag_prefix(self, provenance: str) -> str:
        return self.preview_tag(provenance)

    def provenance_system_preamble(self) -> str:
        return self.build_preamble()


class CoreModuleProvenanceAdapter(DefaultProvenancePort):
    """Wrap lazy-loaded core.provenance module as ProvenancePort."""

    def __init__(self, core: Any):
        self._core = core

    @property
    def PROVENANCE_AUDIT_PREVIEW(self) -> str:
        return self._core.PROVENANCE_AUDIT_PREVIEW

    @property
    def PROVENANCE_LOCAL_FULL(self) -> str:
        return self._core.PROVENANCE_LOCAL_FULL

    @property
    def PROVENANCE_REMOTE_PREVIEW(self) -> str:
        return self._core.PROVENANCE_REMOTE_PREVIEW

    def from_block(self, block: dict) -> str:
        return self._core.provenance_from_block(block)

    def format_fragment(
        self,
        content: str,
        *,
        provenance: str,
        source_peer: str = "",
        block_id: str = "",
    ) -> str:
        return self._core.format_llm_memory_fragment(
            content,
            provenance=provenance,
            source_peer=source_peer,
            block_id=block_id,
        )

    def is_preview(self, provenance: str) -> bool:
        return self._core.is_preview_provenance(provenance)

    def preview_tag(self, provenance: str) -> str:
        return self._core.preview_tag_prefix(provenance)

    def build_preamble(self) -> str:
        return self._core.provenance_system_preamble()

    def block_data_with_provenance(
        self,
        data: dict,
        *,
        provenance: str,
        source_peer: str = "",
        content_kind: Optional[str] = None,
    ) -> dict:
        return self._core.block_data_with_provenance(
            data,
            provenance=provenance,
            source_peer=source_peer,
            content_kind=content_kind,
        )
