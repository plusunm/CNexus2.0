"""Control-plane bootstrap — wire fragment control services + ControlPlaneService."""

from __future__ import annotations

from dataclasses import dataclass

from .conflict_control import ConflictControlHooks, ConflictControlService
from .consensus_control import ConsensusControlHooks, ConsensusControlService
from .control_plane import ControlPlaneService
from .memory_control import MemoryControlHooks, MemoryControlService
from .pruning_control import PruningControlHooks, PruningControlService
from .reflection_control import ReflectionControlHooks, ReflectionControlService
from .rem_control import RemControlHooks, RemControlService
from .replay_control import ReplayControlHooks, ReplayControlService
from .shadow_projection import ShadowProjectionService


@dataclass(frozen=True)
class ControlBootstrapHooks:
    """App-wired hooks for control fragment services."""

    conflict: ConflictControlHooks
    pruning: PruningControlHooks
    consensus: ConsensusControlHooks
    memory: MemoryControlHooks
    replay: ReplayControlHooks
    reflection: ReflectionControlHooks
    rem: RemControlHooks


@dataclass
class ControlBootstrapServices:
    """Constructed control stack."""

    conflict: ConflictControlService
    pruning: PruningControlService
    consensus: ConsensusControlService
    memory: MemoryControlService
    replay: ReplayControlService
    reflection: ReflectionControlService
    rem: RemControlService
    control_plane: ControlPlaneService


def build_control_services(
    shadow: ShadowProjectionService,
    hooks: ControlBootstrapHooks,
) -> ControlBootstrapServices:
    """Wire control fragments and compose ControlPlaneService."""
    conflict = ConflictControlService(hooks.conflict)
    pruning = PruningControlService(hooks.pruning)
    consensus = ConsensusControlService(hooks.consensus)
    memory = MemoryControlService(hooks.memory)
    replay = ReplayControlService(hooks.replay)
    reflection = ReflectionControlService(hooks.reflection)
    rem = RemControlService(hooks.rem)

    control_plane = ControlPlaneService(
        shadow,
        memory,
        replay,
        reflection,
        rem,
        conflict,
        pruning,
        consensus,
    )

    return ControlBootstrapServices(
        conflict=conflict,
        pruning=pruning,
        consensus=consensus,
        memory=memory,
        replay=replay,
        reflection=reflection,
        rem=rem,
        control_plane=control_plane,
    )
