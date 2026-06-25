"""Subsystem status readers — composed fragment services."""

from __future__ import annotations

from .consolidation_status import ConsolidationStatusService
from .replay_status import ReplayStatusService
from .awakening_status import AwakeningStatusService
from .pruning_status import PruningStatusService
from .entropy_status import EntropyStatusService
from .persistence_status import PersistenceStatusService
from .negotiation_conflict_status import NegotiationConflictStatusService
from .reflection_status import ReflectionStatusService
from .conflict_resolution_status import ConflictResolutionStatusService


class StatusSubsystemsService:
    """Gateway-owned L0 subsystem status — zero hooks, pure fragment composition."""

    def __init__(
        self,
        persistence: PersistenceStatusService,
        consolidation: ConsolidationStatusService,
        negotiation_conflict: NegotiationConflictStatusService,
        reflection: ReflectionStatusService,
        replay: ReplayStatusService,
        awakening: AwakeningStatusService,
        pruning: PruningStatusService,
        entropy: EntropyStatusService,
        conflict_resolution: ConflictResolutionStatusService,
    ):
        self._persistence = persistence
        self._consolidation = consolidation
        self._negotiation_conflict = negotiation_conflict
        self._reflection = reflection
        self._replay = replay
        self._awakening = awakening
        self._pruning = pruning
        self._entropy = entropy
        self._conflict_resolution = conflict_resolution

    def persistence_status(self):
        return self._persistence.build()

    def consolidation_status(self):
        return self._consolidation.build()

    def negotiation_conflict_recent(self):
        return self._negotiation_conflict.build_recent()

    def reflection_status(self):
        return self._reflection.build()

    def replay_status(self):
        return self._replay.build(self._awakening.build())

    def awakening_status(self):
        return self._awakening.build()

    def pruning_status(self):
        return self._pruning.build()

    def entropy_status(self):
        return self._entropy.build()

    def conflict_resolution_status(self):
        return self._conflict_resolution.build()
