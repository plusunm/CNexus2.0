"""Spreading-activation memory injection for converse prepare."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..state import EngineStateManager
from .memory.scope import normalize_memory_scope, origin_matches_scope

CollectNodeSpecsFn = Callable[[], List[Dict[str, Any]]]

ActivationHit = Tuple[float, Dict[str, Any]]


@dataclass(frozen=True)
class ActivationHooks:
    collect_node_specs: CollectNodeSpecsFn


class ActivationService:
    """Threshold filtering for spreading activation — formatting lives in MemoryContextService."""

    def __init__(
        self,
        state: EngineStateManager,
        hooks: ActivationHooks,
        *,
        default_threshold: float,
        default_inject_limit: int,
    ):
        self._state = state
        self._hooks = hooks
        self._default_threshold = default_threshold
        self._default_inject_limit = default_inject_limit

    def sync_nodes(self, specs: List[Dict[str, Any]]) -> None:
        def apply(engine: Dict[str, Any]) -> None:
            scores = engine.setdefault("activation", {}).setdefault("scores", {})
            for spec in specs:
                scores.setdefault(spec["id"], 0.0)

        self._state.mutate(apply)

    def overview_items(self) -> List[Dict[str, Any]]:
        """Memory node specs with activation scores for L0 mind overview."""
        specs = self._hooks.collect_node_specs()
        self.sync_nodes(specs)
        scores = self._read_scores()
        cutoff = self._default_threshold
        items: List[Dict[str, Any]] = []
        for spec in specs:
            score = float(scores.get(spec["id"], 0.0))
            row: Dict[str, Any] = {
                **spec,
                "score": round(score, 4),
                "activity": round(score, 4),
                "is_active": score > cutoff,
            }
            if spec.get("node_type"):
                row["node_type"] = spec["node_type"]
            items.append(row)
        return items

    def _read_scores(self) -> Dict[str, float]:
        def read(engine: Dict[str, Any]) -> Dict[str, float]:
            return dict(engine.setdefault("activation", {}).setdefault("scores", {}))

        return self._state.mutate(read)

    def threshold_activated_fragments(
        self,
        limit: Optional[int] = None,
        threshold: Optional[float] = None,
        *,
        memory_scope: str = "local",
        trusted_peers: Optional[Iterable[str]] = None,
    ) -> List[ActivationHit]:
        if limit is None:
            limit = self._default_inject_limit if self._default_inject_limit > 0 else 3
        if limit <= 0:
            return []
        cutoff = float(threshold if threshold is not None else self._default_threshold)
        scope = normalize_memory_scope(memory_scope)
        trusted = set(trusted_peers or [])
        specs = self._hooks.collect_node_specs()
        if scope != "network":
            specs = [
                spec
                for spec in specs
                if origin_matches_scope(str(spec.get("source_peer") or ""), scope, trusted)
            ]
        self.sync_nodes(specs)
        scores = self._read_scores()
        candidates: List[ActivationHit] = []
        for spec in specs:
            score = float(scores.get(spec["id"], 0.0))
            if score > cutoff:
                candidates.append((score, spec))
        candidates.sort(key=lambda item: -item[0])
        return candidates[:limit]
