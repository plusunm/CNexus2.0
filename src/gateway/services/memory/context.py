"""MemoryContextService — LLM prompt context assembly (P4-B)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .provenance import ProvenancePort
from .protection import level_priority
from .types import MemoryFragment, RecallResult, TraceEntry

ActivationHit = Tuple[float, Dict[str, Any]]


class MemoryContextService:
    """Format memory fragments and activation hits for prompt injection."""

    def __init__(
        self,
        provenance: ProvenancePort,
        *,
        default_desc_max: int = 80,
    ):
        self._provenance = provenance
        self._default_desc_max = default_desc_max

    def build(
        self,
        fragments: List[MemoryFragment],
        *,
        trace_entries: Optional[List[TraceEntry]] = None,
        include_provenance: bool = True,
        max_hits: Optional[int] = None,
    ) -> str:
        snippets: List[str] = []
        for fragment in fragments:
            snippet = self._format_fragment_snippet(fragment, include_provenance=include_provenance)
            if snippet:
                snippets.append(snippet)
        for entry in trace_entries or []:
            snippet = self._format_trace_entry(entry, include_provenance=include_provenance)
            if snippet:
                snippets.append(snippet)
        if max_hits is not None:
            snippets = snippets[:max_hits]
        if not snippets:
            return ""
        return "\n---\n".join(snippets)

    def build_recall_context(self, result: RecallResult, *, max_hits: int = 5) -> str:
        body = self.build(
            result.fragments,
            trace_entries=result.trace_entries,
            include_provenance=True,
            max_hits=max_hits,
        )
        if body:
            return body
        query = (result.query or "").strip()
        return f"未检索到与「{query}」相关的记忆片段（个人版 BlockStore 检索）。"

    def format_activation_context(
        self,
        hits: List[ActivationHit],
        desc_max: Optional[int] = None,
    ) -> str:
        if not hits:
            return ""
        max_desc = self._default_desc_max if desc_max is None else int(desc_max)
        lines: List[str] = []
        for i, (score, spec) in enumerate(hits, 1):
            level = str(spec.get("memory_level") or "long_term")
            level_tag = f" · {level}" if level_priority(level) >= level_priority("core") else ""
            lines.append(f"{i}. [{spec['tag']}{level_tag}] {spec['title']} (activation={score:.2f})")
            if max_desc > 0 and spec.get("desc"):
                desc = str(spec["desc"])
                provenance = str(spec.get("provenance") or "")
                if provenance and self._provenance.is_preview(provenance):
                    desc = self._provenance.format_fragment(
                        desc[:max_desc],
                        provenance=provenance,
                        source_peer=str(spec.get("source_peer") or ""),
                        block_id=str(spec.get("id") or ""),
                    )
                else:
                    desc = desc[:max_desc]
                lines.append(f"   {desc}")
        return "\n".join(lines)

    def build_precision_preamble(self, *, enforced: bool = True) -> str:
        if not enforced:
            return ""
        return self._provenance.build_preamble()

    def _format_fragment_snippet(
        self,
        fragment: MemoryFragment,
        *,
        include_provenance: bool,
    ) -> str:
        snippet = fragment.raw_snippet or fragment.snippet
        if not snippet:
            return ""
        if not include_provenance:
            return snippet
        provenance = fragment.provenance or self._provenance.PROVENANCE_LOCAL_FULL
        return self._provenance.format_fragment(
            snippet,
            provenance=provenance,
            source_peer=fragment.source_peer,
            block_id=fragment.block_id,
        )

    def _format_trace_entry(
        self,
        entry: TraceEntry,
        *,
        include_provenance: bool,
    ) -> str:
        text = str(entry.text or "").strip()
        if not text:
            return ""
        if include_provenance and entry.replayed:
            return self._provenance.format_fragment(
                text,
                provenance=self._provenance.PROVENANCE_AUDIT_PREVIEW,
                block_id=entry.trace_id,
            )
        return f"对话记忆：{text}"
