"""Semantic Arbitration Layer (SAL) — conflict resolution + MMR rebalance (P2)."""

from __future__ import annotations

import os
from typing import Dict, List

from .dimensions import (
    DIMENSION_DECISION,
    DIMENSION_FACT,
    DIMENSION_PERSONA_SUMMARY,
    DIMENSION_STYLE,
    default_turn_weights,
    normalize_weights,
)
from .mmr import mmr_select
from .types import (
    ActivationPlan,
    ArbitrationDecision,
    ExclusionRecord,
    PromptPlan,
    RecallPlan,
    SCPRequest,
    SemanticCandidate,
    TurnProfile,
)

_OVERLAP_EXCLUDE_THRESHOLD = float(os.environ.get("CNEXUS_SAL_OVERLAP_THRESHOLD", "0.30"))


class SemanticArbitrationLayer:
    """L1 admission arbitration — SSS enforcement + MMR decorrelation."""

    def arbitrate(self, request: SCPRequest) -> ArbitrationDecision:
        profile = request.turn_profile
        exclusions: List[ExclusionRecord] = []
        recall_items = list(request.recall_candidates)
        prompt_items = list(request.prompt_candidates)
        activation_items = list(request.activation_candidates)

        style_source = _effective_style_source(profile, request.budget_state)
        recall_items, prompt_items, exclusions = _enforce_style_single_source(
            recall_items,
            prompt_items,
            style_source,
            exclusions,
        )

        recall_items, ex = _exclude_dimension(recall_items, DIMENSION_PERSONA_SUMMARY)
        exclusions.extend(ex)

        recall_items, prompt_items, ex = _exclude_high_overlap(recall_items, prompt_items)
        exclusions.extend(ex)

        if _should_mmr(request, recall_items):
            recall_items = mmr_select(
                recall_items,
                request.query,
                limit=_recall_limit(request),
                lambda_relevance=0.68 if request.budget_state.force_mmr_rebalance else 0.74,
                quotas={
                    DIMENSION_FACT: 0.65,
                    DIMENSION_DECISION: 0.25,
                    DIMENSION_STYLE: 0.10 if style_source == "recall" else 0.0,
                },
            )

        weights = _build_weights(profile, request.budget_state, recall_items, prompt_items, style_source)
        violations: List[str] = []
        if style_source == "prompt" and any(c.dimension == DIMENSION_STYLE for c in recall_items):
            violations.append("dual_style_recall")
        if style_source == "recall" and any(c.dimension == DIMENSION_STYLE for c in prompt_items):
            violations.append("dual_style_prompt")

        return ArbitrationDecision(
            recall_plan=RecallPlan(items=recall_items),
            prompt_plan=PromptPlan(items=prompt_items),
            activation_plan=ActivationPlan(items=activation_items),
            exclusions=exclusions,
            dimension_weights=weights,
            violations=violations,
        )


def _effective_style_source(profile: TurnProfile, budget_state) -> str:
    override = getattr(budget_state, "pending_style_source_override", None)
    if override:
        return str(override).lower()
    return str(profile.style_source or "prompt").lower()


def _should_mmr(request: SCPRequest, recall_items: List[SemanticCandidate]) -> bool:
    if getattr(request.budget_state, "force_mmr_rebalance", False):
        return True
    if request.turn_profile.expert_mode and len(recall_items) > 2:
        return True
    return len(recall_items) > 5


def _recall_limit(request: SCPRequest) -> int:
    mode = str(request.turn_profile.converse_mode or "fast").lower()
    if mode == "deep":
        return max(4, int(os.environ.get("CNEXUS_SAL_RECALL_LIMIT_DEEP", "10")))
    return max(3, int(os.environ.get("CNEXUS_SAL_RECALL_LIMIT", "6")))


def _enforce_style_single_source(
    recall_items: List[SemanticCandidate],
    prompt_items: List[SemanticCandidate],
    style_source: str,
    exclusions: List[ExclusionRecord],
) -> tuple[List[SemanticCandidate], List[SemanticCandidate], List[ExclusionRecord]]:
    if style_source == "prompt":
        recall_items, ex = _exclude_dimension(recall_items, DIMENSION_STYLE)
        exclusions.extend(ex)
    elif style_source == "recall":
        prompt_items, ex = _exclude_dimension(prompt_items, DIMENSION_STYLE)
        exclusions.extend(ex)
    else:
        recall_items, ex1 = _exclude_dimension(recall_items, DIMENSION_STYLE)
        prompt_items, ex2 = _exclude_dimension(prompt_items, DIMENSION_STYLE)
        exclusions.extend(ex1 + ex2)
    return recall_items, prompt_items, exclusions


def _exclude_dimension(
    items: List[SemanticCandidate],
    dimension: str,
) -> tuple[List[SemanticCandidate], List[ExclusionRecord]]:
    kept: List[SemanticCandidate] = []
    exclusions: List[ExclusionRecord] = []
    for item in items:
        if item.dimension == dimension:
            exclusions.append(
                ExclusionRecord(
                    reason="sss_single_source",
                    dimension=dimension,
                    block_id=item.block_id,
                    source=item.source,
                )
            )
        else:
            kept.append(item)
    return kept, exclusions


def _exclude_high_overlap(
    recall_items: List[SemanticCandidate],
    prompt_items: List[SemanticCandidate],
) -> tuple[List[SemanticCandidate], List[SemanticCandidate], List[ExclusionRecord]]:
    """Drop lower-dominance side when recall/prompt share near-duplicate content."""
    exclusions: List[ExclusionRecord] = []
    prompt_hashes = {c.content_hash for c in prompt_items if c.content_hash}
    if not prompt_hashes:
        return recall_items, prompt_items, exclusions

    kept_recall: List[SemanticCandidate] = []
    for item in recall_items:
        if item.content_hash and item.content_hash in prompt_hashes and item.dimension != DIMENSION_FACT:
            exclusions.append(
                ExclusionRecord(
                    reason="cross_path_duplicate",
                    dimension=item.dimension,
                    block_id=item.block_id,
                    source=item.source,
                )
            )
        else:
            kept_recall.append(item)
    return kept_recall, prompt_items, exclusions


def _build_weights(
    profile: TurnProfile,
    budget_state,
    recall_items: List[SemanticCandidate],
    prompt_items: List[SemanticCandidate],
    style_source: str,
) -> Dict[str, float]:
    precision = str(profile.thinking_mode or "precision").lower() != "emergent"
    weights = dict(default_turn_weights(precision=precision))

    if any(c.dimension == DIMENSION_STYLE for c in prompt_items + recall_items) and style_source != "off":
        cap = float(getattr(budget_state, "style_weight_max", 0.15))
        weights[DIMENSION_STYLE] = min(cap, weights.get(DIMENSION_STYLE, 0.05) + 0.04)

    weights = normalize_weights(weights)
    fact_floor = float(getattr(budget_state, "fact_floor", 0.75))
    if precision:
        fact = weights.get(DIMENSION_FACT, 0.0)
        decision = weights.get(DIMENSION_DECISION, 0.0)
        if fact + decision < fact_floor:
            delta = fact_floor - (fact + decision)
            weights[DIMENSION_FACT] = fact + delta * 0.7
            weights[DIMENSION_DECISION] = decision + delta * 0.3
            style = weights.get(DIMENSION_STYLE, 0.0)
            if style > 0:
                weights[DIMENSION_STYLE] = max(0.0, style - delta)
            weights = normalize_weights(weights)
    return weights
