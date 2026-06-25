"""Status service bootstrap — wire L0 fragment + infrastructure status stack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..state import EngineStateManager
from .activation import ActivationService
from .api_auth_status import ApiAuthStatusHooks, ApiAuthStatusService
from .assets_status import AssetsStatusHooks, AssetsStatusService
from .audit_chain_status import AuditChainStatusHooks, AuditChainStatusService
from .awakening_status import AwakeningStatusHooks, AwakeningStatusService
from .consensus_status import ConsensusStatusHooks, ConsensusStatusService
from .consolidation_status import ConsolidationStatusHooks, ConsolidationStatusService
from .conflict_resolution_status import ConflictResolutionStatusHooks, ConflictResolutionStatusService
from .dashboard_status import DashboardStatusHooks, DashboardStatusService
from .entropy_status import EntropyStatusHooks, EntropyStatusService
from .identity_status import IdentityStatusHooks, IdentityStatusService
from .negotiation_conflict_status import NegotiationConflictStatusHooks, NegotiationConflictStatusService
from .network_status import NetworkStatusHooks, NetworkStatusService
from .peers_status import PeersStatusHooks, PeersStatusService
from .persistence_status import PersistenceStatusHooks, PersistenceStatusService
from .pruning_status import PruningStatusHooks, PruningStatusService
from .reflection_status import ReflectionStatusHooks, ReflectionStatusService
from .replay_status import ReplayStatusHooks, ReplayStatusService
from .resilience_status import ResilienceStatusHooks, ResilienceStatusService
from .shadow_projection import ShadowProjectionHooks, ShadowProjectionService
from .status_snapshot import StatusSnapshotService
from .status_subsystems import StatusSubsystemsService


@dataclass(frozen=True)
class StatusBootstrapHooks:
    """App-wired hooks for the full status stack."""

    consolidation: ConsolidationStatusHooks
    replay: ReplayStatusHooks
    awakening: AwakeningStatusHooks
    pruning: PruningStatusHooks
    entropy: EntropyStatusHooks
    persistence: PersistenceStatusHooks
    negotiation_conflict: NegotiationConflictStatusHooks
    reflection: ReflectionStatusHooks
    conflict_resolution: ConflictResolutionStatusHooks
    network: NetworkStatusHooks
    identity: IdentityStatusHooks
    audit_chain: AuditChainStatusHooks
    api_auth: ApiAuthStatusHooks
    consensus: ConsensusStatusHooks
    assets: AssetsStatusHooks
    resilience: ResilienceStatusHooks
    peers: PeersStatusHooks
    dashboard: DashboardStatusHooks
    shadow: ShadowProjectionHooks


@dataclass
class StatusBootstrapServices:
    """Constructed status services — fragment + composed layers."""

    consolidation: ConsolidationStatusService
    replay: ReplayStatusService
    awakening: AwakeningStatusService
    pruning: PruningStatusService
    entropy: EntropyStatusService
    persistence: PersistenceStatusService
    negotiation_conflict: NegotiationConflictStatusService
    reflection: ReflectionStatusService
    conflict_resolution: ConflictResolutionStatusService
    subsystems: StatusSubsystemsService
    network: NetworkStatusService
    identity: IdentityStatusService
    audit_chain: AuditChainStatusService
    api_auth: ApiAuthStatusService
    consensus: ConsensusStatusService
    assets: AssetsStatusService
    resilience: ResilienceStatusService
    peers: PeersStatusService
    snapshot: StatusSnapshotService
    dashboard: DashboardStatusService
    shadow: ShadowProjectionService


def build_status_services(
    state: EngineStateManager,
    activation: ActivationService,
    hooks: StatusBootstrapHooks,
) -> StatusBootstrapServices:
    """Wire subsystem fragments, infrastructure readers, snapshot, and dashboard."""
    consolidation = ConsolidationStatusService(state, hooks.consolidation)
    replay = ReplayStatusService(state, hooks.replay)
    awakening = AwakeningStatusService(hooks.awakening)
    pruning = PruningStatusService(hooks.pruning)
    entropy = EntropyStatusService(hooks.entropy)
    persistence = PersistenceStatusService(state, hooks.persistence)
    negotiation_conflict = NegotiationConflictStatusService(state, hooks.negotiation_conflict)
    reflection = ReflectionStatusService(hooks.reflection)
    conflict_resolution = ConflictResolutionStatusService(state, hooks.conflict_resolution)

    subsystems = StatusSubsystemsService(
        persistence,
        consolidation,
        negotiation_conflict,
        reflection,
        replay,
        awakening,
        pruning,
        entropy,
        conflict_resolution,
    )

    network = NetworkStatusService(hooks.network)
    identity = IdentityStatusService(hooks.identity)
    audit_chain = AuditChainStatusService(hooks.audit_chain)
    api_auth = ApiAuthStatusService(hooks.api_auth)
    consensus = ConsensusStatusService(hooks.consensus)
    assets = AssetsStatusService(hooks.assets)
    resilience = ResilienceStatusService(hooks.resilience, audit_chain)
    peers = PeersStatusService(hooks.peers, network)

    snapshot = StatusSnapshotService(
        state,
        subsystems,
        peers,
        resilience,
        identity,
        audit_chain,
        api_auth,
        consensus,
        assets,
        activation,
    )

    dashboard = DashboardStatusService(
        state,
        subsystems,
        identity,
        audit_chain,
        consensus,
        hooks.dashboard,
    )

    shadow = ShadowProjectionService(state, snapshot, hooks.shadow)

    return StatusBootstrapServices(
        consolidation=consolidation,
        replay=replay,
        awakening=awakening,
        pruning=pruning,
        entropy=entropy,
        persistence=persistence,
        negotiation_conflict=negotiation_conflict,
        reflection=reflection,
        conflict_resolution=conflict_resolution,
        subsystems=subsystems,
        network=network,
        identity=identity,
        audit_chain=audit_chain,
        api_auth=api_auth,
        consensus=consensus,
        assets=assets,
        resilience=resilience,
        peers=peers,
        snapshot=snapshot,
        dashboard=dashboard,
        shadow=shadow,
    )
