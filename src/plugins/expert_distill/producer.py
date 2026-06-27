"""Expert candidate producer — builds SCP recall/prompt plans from tagged blocks."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from semantic.dimensions import (
    DIMENSION_DECISION,
    DIMENSION_FACT,
    DIMENSION_PERSONA_SUMMARY,
    DIMENSION_PROCEDURE,
    DIMENSION_STYLE,
)
from semantic.types import SemanticCandidate

_STYLE_LABELS = frozenset({"narrative", "reflective"})
_FACT_LABELS = frozenset({"semantic", "archival", "belief"})


def expert_distill_enabled() -> bool:
    raw = os.environ.get("CNEXUS_EXPERT_DISTILL", "0")
    return str(raw).lower() not in ("0", "false", "no", "")


def _block_text(block: Mapping[str, Any]) -> str:
    data = dict(block.get("data") or {})
    return str(
        data.get("content")
        or data.get("response_text")
        or data.get("summary")
        or data.get("filename")
        or ""
    ).strip()


def _infer_dimension(block: Mapping[str, Any]) -> str:
    data = dict(block.get("data") or {})
    explicit = str(data.get("semantic_dimension") or data.get("distill_mode") or "").strip().lower()
    if explicit in {
        DIMENSION_FACT,
        DIMENSION_DECISION,
        DIMENSION_STYLE,
        DIMENSION_PROCEDURE,
        DIMENSION_PERSONA_SUMMARY,
    }:
        return explicit
    label = str(block.get("label") or "").strip().lower()
    if label in _STYLE_LABELS or str(data.get("injection_role") or "") == "guide":
        return DIMENSION_STYLE
    if label == "intent":
        return DIMENSION_PROCEDURE
    if label in _FACT_LABELS:
        return DIMENSION_FACT
    return DIMENSION_FACT


def _subject_matches(block: Mapping[str, Any], subject_id: str) -> bool:
    data = dict(block.get("data") or {})
    sid = str(data.get("subject_id") or data.get("expert_id") or "").strip()
    if sid and sid == subject_id:
        return True
    if str(data.get("plugin") or "") == "expert_distill" and not sid:
        return True
    return False


def _score_block(query: str, text: str) -> float:
    q_tokens = {t for t in re.findall(r"[\w\u4e00-\u9fff]+", query.lower()) if len(t) >= 2}
    if not q_tokens:
        return 0.5
    body = text.lower()
    hits = sum(1 for t in q_tokens if t in body)
    return min(1.0, hits / max(1, len(q_tokens)))


class ExpertCandidateProducer:
    """Produce SCP candidates from BlockStore rows — never composes LLM context."""

    def produce(
        self,
        blocks: List[Mapping[str, Any]],
        *,
        query: str,
        subject_id: str,
        style_source: str = "prompt",
    ) -> Tuple[List[SemanticCandidate], List[SemanticCandidate], int]:
        subject = str(subject_id or "").strip()
        if not subject:
            return [], [], 0

        recall: List[SemanticCandidate] = []
        prompt: List[SemanticCandidate] = []
        fact_hits = 0

        for block in blocks:
            if not _subject_matches(block, subject):
                continue
            text = _block_text(block)
            if len(text) < 8:
                continue
            dim = _infer_dimension(block)
            block_id = str(block.get("block_id") or "")
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            score = _score_block(query, text)
            candidate = SemanticCandidate(
                block_id=block_id,
                dimension=dim,
                content=text[:480],
                score=score,
                source="recall" if dim in (DIMENSION_FACT, DIMENSION_DECISION) else "prompt",
                subject_id=subject,
                content_hash=content_hash,
            )
            if dim in (DIMENSION_FACT, DIMENSION_DECISION):
                recall.append(candidate)
                if dim == DIMENSION_FACT and score > 0:
                    fact_hits += 1
            elif dim == DIMENSION_STYLE and style_source == "recall":
                recall.append(candidate)
            elif dim in (DIMENSION_STYLE, DIMENSION_PROCEDURE, DIMENSION_PERSONA_SUMMARY):
                prompt.append(candidate)

        return recall, prompt, fact_hits
