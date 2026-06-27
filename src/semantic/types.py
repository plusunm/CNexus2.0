"""SCP protocol models — frozen interface contract for parallel development."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

ComposeLlmContextFn = Callable[[str], str]


@dataclass(frozen=True)
class TurnProfile:
    thinking_mode: str = "precision"
    converse_mode: str = "fast"
    memory_scope: str = "local"
    expert_mode: Optional[str] = None
    style_source: str = "prompt"  # prompt | recall | off


@dataclass(frozen=True)
class SlotBudget:
    procedure_max_tokens: int = 200
    style_max_tokens: int = 150
    recall_max_tokens: int = 1200
    activation_max_tokens: int = 400


@dataclass
class SemanticCandidate:
    block_id: str = ""
    dimension: str = "fact"
    content: str = ""
    score: float = 1.0
    source: str = "recall"  # recall | prompt | activation
    subject_id: str = ""
    content_hash: str = ""


@dataclass
class RecallPlan:
    items: List[SemanticCandidate] = field(default_factory=list)


@dataclass
class PromptPlan:
    items: List[SemanticCandidate] = field(default_factory=list)


@dataclass
class ActivationPlan:
    items: List[SemanticCandidate] = field(default_factory=list)


@dataclass
class ExclusionRecord:
    reason: str
    dimension: str = ""
    block_id: str = ""
    source: str = ""


@dataclass
class ArbitrationDecision:
    recall_plan: RecallPlan = field(default_factory=RecallPlan)
    prompt_plan: PromptPlan = field(default_factory=PromptPlan)
    activation_plan: ActivationPlan = field(default_factory=ActivationPlan)
    exclusions: List[ExclusionRecord] = field(default_factory=list)
    dimension_weights: Dict[str, float] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)


@dataclass
class DriftObservation:
    cross_path_overlap_ratio: float = 0.0
    style_weight: float = 0.0
    fact_miss_streak: int = 0
    triggers: List[str] = field(default_factory=list)
    entanglement_score: float = 0.0
    dual_path_risk: bool = False


@dataclass
class BudgetCorrection:
    style_weight_max: float = 0.15
    fact_floor: float = 0.75
    style_source_override: Optional[str] = None
    force_mmr_rebalance: bool = False
    freeze_style_until_turn: int = 0
    trigger_id: str = ""
    level: int = 0


@dataclass
class SemanticBudgetState:
    session_id: str = "default"
    turn_count: int = 0
    ema: Dict[str, float] = field(default_factory=dict)
    cumulative: Dict[str, float] = field(default_factory=dict)
    correction_active: bool = False
    freeze_style_until_turn: int = 0
    last_correction: Optional[str] = None
    style_weight_max: float = 0.15
    fact_floor: float = 0.75
    style_rise_streak: int = 0
    prev_ema_style: float = 0.0
    fact_miss_streak: int = 0
    force_mmr_rebalance: bool = False
    pending_style_source_override: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_count": int(self.turn_count),
            "ema": dict(self.ema),
            "cumulative": dict(self.cumulative),
            "correction_active": bool(self.correction_active),
            "freeze_style_until_turn": int(self.freeze_style_until_turn),
            "last_correction": self.last_correction,
            "style_weight_max": float(self.style_weight_max),
            "fact_floor": float(self.fact_floor),
            "style_rise_streak": int(self.style_rise_streak),
            "prev_ema_style": float(self.prev_ema_style),
            "fact_miss_streak": int(self.fact_miss_streak),
            "force_mmr_rebalance": bool(self.force_mmr_rebalance),
            "pending_style_source_override": self.pending_style_source_override,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SemanticBudgetState":
        payload = dict(data or {})
        return cls(
            session_id=str(payload.get("session_id") or "default"),
            turn_count=int(payload.get("turn_count") or 0),
            ema={str(k): float(v) for k, v in dict(payload.get("ema") or {}).items()},
            cumulative={str(k): float(v) for k, v in dict(payload.get("cumulative") or {}).items()},
            correction_active=bool(payload.get("correction_active")),
            freeze_style_until_turn=int(payload.get("freeze_style_until_turn") or 0),
            last_correction=payload.get("last_correction"),
            style_weight_max=float(payload.get("style_weight_max") or 0.15),
            fact_floor=float(payload.get("fact_floor") or 0.75),
            style_rise_streak=int(payload.get("style_rise_streak") or 0),
            prev_ema_style=float(payload.get("prev_ema_style") or 0.0),
            fact_miss_streak=int(payload.get("fact_miss_streak") or 0),
            force_mmr_rebalance=bool(payload.get("force_mmr_rebalance")),
            pending_style_source_override=payload.get("pending_style_source_override"),
        )


@dataclass(frozen=True)
class SCPRequest:
    query: str
    turn_profile: TurnProfile
    activation_context: str = ""
    recall_candidates: List[SemanticCandidate] = field(default_factory=list)
    prompt_candidates: List[SemanticCandidate] = field(default_factory=list)
    activation_candidates: List[SemanticCandidate] = field(default_factory=list)
    budget_state: SemanticBudgetState = field(default_factory=SemanticBudgetState)
    slot_budget: SlotBudget = field(default_factory=SlotBudget)
    compose_llm_context: Optional[ComposeLlmContextFn] = None
    fact_hits: int = 0


@dataclass(frozen=True)
class SCPResponse:
    llm_context: str
    decision: ArbitrationDecision
    observation: DriftObservation
    budget_state: SemanticBudgetState
    correction: Optional[BudgetCorrection] = None
    admitted: bool = True
    reject_reason: Optional[str] = None
