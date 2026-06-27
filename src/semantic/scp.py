"""Semantic Control Plane orchestrator — SCP.admit() single entry."""

from __future__ import annotations

import os

from .arbitration import SemanticArbitrationLayer
from .budget_store import SemanticBudgetStore
from .composer import ContextComposer
from .drift_observation import DriftObserver
from .provenance_gate import ProvenanceGate
from .stability_loop import SemanticBudgetStabilityLoop
from .types import SCPRequest, SCPResponse, TurnProfile


def scp_enabled() -> bool:
    raw = os.environ.get("CNEXUS_SCP_ENABLED", "0")
    return str(raw).lower() not in ("0", "false", "no", "")


class SemanticControlPlane:
    """Kernel-adjacent admission controller for cognition injection."""

    def __init__(
        self,
        *,
        store: SemanticBudgetStore | None = None,
        sal: SemanticArbitrationLayer | None = None,
        composer: ContextComposer | None = None,
        observer: DriftObserver | None = None,
        sbsl: SemanticBudgetStabilityLoop | None = None,
        persist: bool = True,
    ):
        self._store = store or SemanticBudgetStore()
        self._sal = sal or SemanticArbitrationLayer()
        self._composer = composer or ContextComposer()
        self._observer = observer or DriftObserver()
        self._sbsl = sbsl or SemanticBudgetStabilityLoop()
        self._provenance = ProvenanceGate()
        self._persist = persist

    def load_budget_state(self) -> "SemanticBudgetState":
        from .types import SemanticBudgetState

        return self._store.load() if self._persist else SemanticBudgetState()

    def admit(self, request: SCPRequest) -> SCPResponse:
        budget_state = request.budget_state
        profile = _apply_budget_corrections(request.turn_profile, budget_state, self._sbsl)

        req = SCPRequest(
            query=request.query,
            turn_profile=profile,
            activation_context=request.activation_context,
            recall_candidates=request.recall_candidates,
            prompt_candidates=request.prompt_candidates,
            activation_candidates=request.activation_candidates,
            budget_state=budget_state,
            slot_budget=request.slot_budget,
            compose_llm_context=request.compose_llm_context,
            fact_hits=request.fact_hits,
        )

        decision = self._sal.arbitrate(req)
        if decision.violations:
            return SCPResponse(
                llm_context=_fallback_context(req),
                decision=decision,
                observation=self._observer.observe(req, decision),
                budget_state=budget_state,
                admitted=False,
                reject_reason=";".join(decision.violations),
            )

        memory_layer = self._composer.compose(req, decision)
        memory_layer = self._provenance.apply(memory_layer, request=req, decision=decision)
        llm_context = _finalize_context(req, memory_layer)
        observation = self._observer.observe(req, decision)
        observation.fact_miss_streak = _merged_fact_miss_streak(budget_state, observation.fact_miss_streak)

        budget_state = self._sbsl.update_ema(budget_state, decision.dimension_weights)
        budget_state = _apply_observation_streak(budget_state, observation.fact_miss_streak)
        budget_state, correction = self._sbsl.evaluate(budget_state, observation)
        budget_state = _apply_correction_state(budget_state, correction)

        if self._persist:
            self._store.save(budget_state)

        return SCPResponse(
            llm_context=llm_context,
            decision=decision,
            observation=observation,
            budget_state=budget_state,
            correction=correction,
            admitted=True,
        )


def _apply_budget_corrections(profile: TurnProfile, budget_state, sbsl: SemanticBudgetStabilityLoop) -> TurnProfile:
    style_source = str(profile.style_source or "prompt")
    pending = getattr(budget_state, "pending_style_source_override", None)
    if pending:
        style_source = str(pending)
    if sbsl.is_style_frozen(budget_state):
        style_source = "off"
    if style_source == profile.style_source and not pending and not sbsl.is_style_frozen(budget_state):
        return profile
    return TurnProfile(
        thinking_mode=profile.thinking_mode,
        converse_mode=profile.converse_mode,
        memory_scope=profile.memory_scope,
        expert_mode=profile.expert_mode,
        style_source=style_source,
    )


def _fallback_context(request: SCPRequest) -> str:
    compose = request.compose_llm_context
    if compose is None:
        return str(request.activation_context or "")
    return compose(str(request.activation_context or ""))


def _finalize_context(request: SCPRequest, memory_layer: str) -> str:
    compose = request.compose_llm_context
    if compose is None:
        return str(memory_layer or "")
    return compose(str(memory_layer or ""))


def _merged_fact_miss_streak(budget_state, observation_streak: int) -> int:
    if observation_streak <= 0:
        return 0
    return int(budget_state.fact_miss_streak) + observation_streak


def _apply_observation_streak(budget_state, streak: int):
    from dataclasses import replace

    return replace(budget_state, fact_miss_streak=int(streak))


def _apply_correction_state(budget_state, correction):
    from dataclasses import replace

    if correction is None:
        return replace(
            budget_state,
            force_mmr_rebalance=False,
            pending_style_source_override=None,
        )
    pending = correction.style_source_override
    return replace(
        budget_state,
        force_mmr_rebalance=bool(correction.force_mmr_rebalance),
        pending_style_source_override=pending,
    )
