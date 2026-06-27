"""Maximal Marginal Relevance selection — decorrelated recall (SCP P2)."""

from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

from .dimensions import DIMENSION_DECISION, DIMENSION_FACT, DIMENSION_STYLE
from .types import SemanticCandidate

TokenizeFn = Callable[[str], Set[str]]


def _tokenize(text: str) -> Set[str]:
    return {t for t in re.findall(r"[\w\u4e00-\u9fff]+", str(text or "").lower()) if len(t) >= 2}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def query_similarity(query: str, candidate: SemanticCandidate) -> float:
    q = _tokenize(query)
    body = _tokenize(f"{candidate.content} {candidate.block_id}")
    if not q:
        return float(candidate.score or 0.5)
    overlap = len(q & body) / max(1, len(q))
    return 0.65 * overlap + 0.35 * min(1.0, float(candidate.score or 0.5))


def mmr_select(
    candidates: Sequence[SemanticCandidate],
    query: str,
    *,
    limit: int = 8,
    lambda_relevance: float = 0.72,
    quotas: Optional[Dict[str, float]] = None,
) -> List[SemanticCandidate]:
    """Greedy MMR with optional per-dimension quotas."""
    pool = list(candidates)
    if not pool or limit <= 0:
        return []

    tokenized = [(c, _tokenize(c.content)) for c in pool]
    selected: List[SemanticCandidate] = []
    selected_tokens: List[Set[str]] = []
    counts: Dict[str, int] = {}

    default_quotas = {
        DIMENSION_FACT: 0.60,
        DIMENSION_DECISION: 0.30,
        DIMENSION_STYLE: 0.10,
    }
    qmap = dict(default_quotas)
    if quotas:
        qmap.update(quotas)

    while pool and len(selected) < limit:
        best_idx = -1
        best_score = -1.0
        for idx, (candidate, tokens) in enumerate(tokenized):
            if candidate not in pool:
                continue
            dim = str(candidate.dimension or DIMENSION_FACT)
            max_for_dim = max(1, int(limit * float(qmap.get(dim, 0.2))))
            if counts.get(dim, 0) >= max_for_dim:
                continue

            rel = query_similarity(query, candidate)
            redundancy = 0.0
            if selected_tokens:
                redundancy = max(_jaccard(tokens, st) for st in selected_tokens)
            mmr = lambda_relevance * rel - (1.0 - lambda_relevance) * redundancy
            if mmr > best_score:
                best_score = mmr
                best_idx = idx

        if best_idx < 0:
            break
        chosen, chosen_tokens = tokenized[best_idx]
        selected.append(chosen)
        selected_tokens.append(chosen_tokens)
        counts[str(chosen.dimension or DIMENSION_FACT)] = counts.get(str(chosen.dimension), 0) + 1
        pool.remove(chosen)

    return selected
