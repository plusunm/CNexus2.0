"""Expert distillation plugin — candidate producer only (hot-plug)."""

from .producer import ExpertCandidateProducer, expert_distill_enabled
from .service import ExpertDistillService, fact_confirm_block

__all__ = [
    "ExpertCandidateProducer",
    "ExpertDistillService",
    "expert_distill_enabled",
    "fact_confirm_block",
]
