"""MemoryQueryService — BlockStore + trace search (Memory Domain read path)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ...state import EngineStateManager
from .context import MemoryContextService
from .project import block_visible_for_active_project, normalize_active_project
from .provenance import DefaultProvenancePort, ProvenancePort
from .scope import normalize_memory_scope, origin_matches_scope
from .types import MemoryFragment, MemoryRecallHooks, QueryFilters, RecallResult, TraceEntry


def _origin_matches_scope(source_peer: str, scope: str, trusted: Set[str]) -> bool:
    return origin_matches_scope(source_peer, scope, trusted)


def _block_content(data: Dict[str, Any]) -> str:
    return str(data.get("content") or data.get("response_text") or data.get("filename") or "")


def _block_haystack(block: Dict[str, Any]) -> str:
    data = dict(block.get("data") or {})
    block_id = str(block.get("block_id") or "")
    return " ".join(
        str(part or "")
        for part in (
            block_id,
            _block_content(data),
            data.get("tag"),
            data.get("title"),
            data.get("filename"),
        )
    ).lower()


class MemoryQueryService:
    """Unified memory read/search — no app_v2 imports."""

    def __init__(
        self,
        state: EngineStateManager,
        hooks: MemoryRecallHooks,
        *,
        provenance: Optional[ProvenancePort] = None,
        context: Optional[MemoryContextService] = None,
        assets: Any = None,
        default_filters: Optional[QueryFilters] = None,
        max_hits: Optional[int] = None,
        block_snippet_chars: Optional[int] = None,
        trace_snippet_chars: Optional[int] = None,
    ):
        self._state = state
        self._hooks = hooks
        self._provenance = provenance or DefaultProvenancePort()
        self._context = context or MemoryContextService(self._provenance)
        self._assets = assets
        base = default_filters or QueryFilters()
        if max_hits is not None or block_snippet_chars is not None or trace_snippet_chars is not None:
            base = QueryFilters(
                limit=max_hits if max_hits is not None else base.limit,
                scope=base.scope,
                trusted_peers=base.trusted_peers,
                block_snippet_chars=block_snippet_chars if block_snippet_chars is not None else base.block_snippet_chars,
                trace_snippet_chars=trace_snippet_chars if trace_snippet_chars is not None else base.trace_snippet_chars,
            )
        self._default_filters = base

    def attach_assets(self, assets: Any) -> None:
        self._assets = assets

    def recall(self, query: str, *, filters: Optional[QueryFilters] = None) -> Dict[str, str]:
        """Legacy API — returns ``{"context": ...}`` for pipeline and HTTP routes."""
        filt = filters or self._default_filters
        result = self.search(query, filters=filt)
        return {"context": self._context.build_recall_context(result, max_hits=filt.limit)}

    def search(self, query: str, *, filters: Optional[QueryFilters] = None) -> RecallResult:
        filt = filters or self._default_filters
        q = (query or "").strip()
        q_lower = q.lower()

        def _read(engine: Dict[str, Any]) -> RecallResult:
            fragments = self._search_blocks(engine, q_lower, filt)
            trace_entries: List[TraceEntry] = []
            if not fragments and q_lower:
                trace_entries = self._search_trace(engine, q_lower, filt)
            return RecallResult(query=q, fragments=fragments, trace_entries=trace_entries)

        return self._state.mutate(_read)

    def search_block_rows(
        self,
        memory_store: Any,
        query: str,
        *,
        scope: str = "local",
        trusted: Optional[Set[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Asset search merge rows — unified BlockStore substring search."""
        q = str(query or "").strip().lower()
        if not q or memory_store is None:
            return []
        trusted_set = trusted or set()
        filt = QueryFilters(limit=limit, scope=scope, trusted_peers=frozenset(trusted_set))
        engine = {"memory_store": memory_store, "trace": []}
        fragments = self._search_blocks(engine, q, filt, format_for_llm=False)
        return [frag.to_search_row() for frag in fragments]

    def _search_blocks(
        self,
        engine: Dict[str, Any],
        q_lower: str,
        filt: QueryFilters,
        *,
        blocks_override: Optional[List[Any]] = None,
        format_for_llm: bool = True,
    ) -> List[MemoryFragment]:
        hooks = self._hooks
        prov = self._provenance
        prune = hooks.get_cognitive_pruning_engine()
        trusted = set(filt.trusted_peers)
        active_project = normalize_active_project(engine.get("active_project"))
        memory_store = engine["memory_store"]
        blocks = blocks_override if blocks_override is not None else memory_store.blocks
        fragments: List[MemoryFragment] = []

        for block in blocks:
            if not block_visible_for_active_project(block, active_project):
                continue
            if prune and not prune.block_is_active(block):
                continue
            try:
                from .protection import is_recall_excluded_block
            except ImportError:
                is_recall_excluded_block = lambda _b: False  # type: ignore[assignment,misc]
            if is_recall_excluded_block(block):
                continue
            data = dict(block.get("data") or {})
            source_peer = str(data.get("source_peer") or "").strip()
            if not _origin_matches_scope(source_peer, filt.scope, trusted):
                continue

            asset_id = str(data.get("asset_id") or "").strip()
            assets = self._assets
            if (
                asset_id
                and assets is not None
                and not assets.blob_present(asset_id)
                and assets.peer_pull_enabled()
                and source_peer
            ):
                assets.ensure_local_for_recall(asset_id, source_peer=source_peer)
                data = dict(block.get("data") or {})

            content = _block_content(data)
            if q_lower and q_lower not in _block_haystack(block):
                continue

            block_id = str(block.get("block_id") or "")
            raw_snippet = content[: filt.block_snippet_chars]
            provenance = prov.from_block(block)
            snippet = raw_snippet
            if format_for_llm:
                snippet = prov.format_fragment(
                    raw_snippet,
                    provenance=provenance,
                    source_peer=source_peer,
                    block_id=block_id,
                )

            origin = "local"
            if source_peer:
                origin = "trusted" if source_peer in trusted else "network"

            fragments.append(
                MemoryFragment(
                    block_id=block_id,
                    content=content,
                    snippet=snippet,
                    raw_snippet=raw_snippet,
                    provenance=provenance,
                    source_peer=source_peer,
                    asset_id=asset_id,
                    tag=str(data.get("tag") or data.get("meta") or data.get("title") or block_id[:16]),
                    memory_origin=origin,
                )
            )
            if len(fragments) >= filt.limit:
                break
        return fragments

    def _search_trace(self, engine: Dict[str, Any], q_lower: str, filt: QueryFilters) -> List[TraceEntry]:
        hits: List[TraceEntry] = []
        for entry in reversed(engine.get("trace", [])):
            inp = str(entry.get("input") or "")
            if q_lower not in inp.lower():
                continue
            hits.append(
                TraceEntry(
                    text=inp[: filt.trace_snippet_chars],
                    replayed=bool(entry.get("replayed")),
                    trace_id=str(entry.get("trace_id") or ""),
                )
            )
            if len(hits) >= filt.limit:
                break
        return hits


# Backward-compatible alias used by pipeline, routes, and app_v2 wiring.
MemoryRecallService = MemoryQueryService
