"""Memory Domain shared types — fragments, recall results, query filters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, List, Optional

GetPruningEngineFn = Callable[[], Any]


@dataclass(frozen=True)
class MemoryRecallHooks:
    """I/O hooks for pruning filter — provenance lives on ProvenancePort."""

    get_cognitive_pruning_engine: GetPruningEngineFn


@dataclass(frozen=True)
class TraceEntry:
    text: str
    replayed: bool = False
    trace_id: str = ""


@dataclass(frozen=True)
class QueryFilters:
    limit: int = 5
    scope: str = "local"
    trusted_peers: FrozenSet[str] = field(default_factory=frozenset)
    block_snippet_chars: int = 240
    trace_snippet_chars: int = 200


@dataclass(frozen=True)
class MemoryFragment:
    block_id: str
    content: str
    snippet: str
    source_peer: str = ""
    asset_id: str = ""
    tag: str = ""
    kind: str = "memory"
    memory_origin: str = "local"
    score: float = 1.0
    provenance: str = ""
    raw_snippet: str = ""

    def to_search_row(self) -> Dict[str, Any]:
        """Asset search UI row shape (compatible with federated merge)."""
        return {
            "kind": self.kind,
            "block_id": self.block_id,
            "asset_id": self.asset_id,
            "type": "memory",
            "filename": self.tag or self.block_id[:16],
            "summary": self.snippet[:160] or self.block_id[:48],
            "desc": self.tag,
            "source_peer": self.source_peer or None,
            "peer_host": None,
            "local_blob": True,
            "memory_origin": self.memory_origin,
            "score": self.score,
        }


@dataclass
class RecallResult:
    query: str
    fragments: List[MemoryFragment] = field(default_factory=list)
    trace_entries: List[TraceEntry] = field(default_factory=list)

    def hit_snippets(self, *, max_hits: Optional[int] = None) -> List[str]:
        combined = [f.raw_snippet or f.snippet for f in self.fragments] + [
            entry.text for entry in self.trace_entries
        ]
        if max_hits is not None:
            return combined[:max_hits]
        return combined

    def to_legacy_context(self, *, max_hits: int = 5, context: Any = None) -> Dict[str, str]:
        if context is not None:
            return {"context": context.build_recall_context(self, max_hits=max_hits)}
        snippets = self.hit_snippets(max_hits=max_hits)
        if snippets:
            return {"context": "\n---\n".join(snippets)}
        return {
            "context": f"未检索到与「{self.query}」相关的记忆片段（个人版 BlockStore 检索）。",
        }
