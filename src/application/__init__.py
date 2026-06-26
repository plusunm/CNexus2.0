"""Application Layer — unified semantic facade over cognitive / catalog / storage / repair."""

from .facade import ApplicationFacade
from .state import (
    PHASE_CONNECTED,
    PHASE_DIAGNOSED,
    PHASE_GATE_PREVIEW,
    PHASE_IDLE,
    PHASE_PUBLISHED,
    PHASE_REPAIR_COMPLETE,
    PHASE_REPAIR_PENDING,
    ApplicationControlState,
)

__all__ = [
    "ApplicationFacade",
    "ApplicationControlState",
    "PHASE_IDLE",
    "PHASE_CONNECTED",
    "PHASE_DIAGNOSED",
    "PHASE_GATE_PREVIEW",
    "PHASE_REPAIR_PENDING",
    "PHASE_REPAIR_COMPLETE",
    "PHASE_PUBLISHED",
]
