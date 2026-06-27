#!/usr/bin/env python3
"""CNexus 2.0 Pure Gateway — L0-spec HTTP server, zero legacy import conflicts."""

import os, sys, json, math, time, traceback, cgi, shutil, subprocess, threading, ast, base64, re, tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from urllib import request as urlrequest

# ── Phase 4 纯函数 kernel 加载 ─────────────────────────────────────────
# 绕过 src/__init__.py（它会尝试 import 旧 CNexusOSKernel 然后炸裂）
KERNEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "kernel")
CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "core")
NETWORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "network")

API_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "api")
GATEWAY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "gateway")

def _bootstrap_gateway_modules():
    """Load src/gateway as cnexus_gateway package (avoids src/__init__.py conflicts)."""
    import importlib.util as u
    pkg = "cnexus_gateway"
    if pkg not in sys.modules:
        init_path = os.path.join(GATEWAY_DIR, "__init__.py")
        spec = u.spec_from_file_location(pkg, init_path, submodule_search_locations=[GATEWAY_DIR])
        module = u.module_from_spec(spec)
        sys.modules[pkg] = module
        spec.loader.exec_module(module)

    def _load(subfile, fullname, package):
        path = os.path.join(GATEWAY_DIR, subfile)
        spec = u.spec_from_file_location(fullname, path)
        mod = u.module_from_spec(spec)
        mod.__package__ = package
        sys.modules[fullname] = mod
        spec.loader.exec_module(mod)
        return mod

    state_mod = _load("state.py", f"{pkg}.state", pkg)
    svc_mod = _load(os.path.join("services", "models.py"), f"{pkg}.services.models", f"{pkg}.services")
    routes_mod = _load(os.path.join("routes", "models.py"), f"{pkg}.routes.models", f"{pkg}.routes")
    ingest_mod = _load(os.path.join("services", "ingest.py"), f"{pkg}.services.ingest", f"{pkg}.services")
    ingest_routes_mod = _load(os.path.join("routes", "ingest.py"), f"{pkg}.routes.ingest", f"{pkg}.routes")
    converse_mod = _load(os.path.join("services", "converse.py"), f"{pkg}.services.converse", f"{pkg}.services")
    converse_events_mod = _load(
        os.path.join("services", "converse_events.py"),
        f"{pkg}.services.converse_events",
        f"{pkg}.services",
    )
    converse_routes_mod = _load(os.path.join("routes", "converse.py"), f"{pkg}.routes.converse", f"{pkg}.routes")
    llm_mod = _load(os.path.join("services", "llm.py"), f"{pkg}.services.llm", f"{pkg}.services")
    converse_thinking_mod = _load(
        os.path.join("services", "converse_thinking.py"),
        f"{pkg}.services.converse_thinking",
        f"{pkg}.services",
    )
    converse_speech_mod = _load(
        os.path.join("services", "converse_speech.py"),
        f"{pkg}.services.converse_speech",
        f"{pkg}.services",
    )
    converse_config_mod = _load(
        os.path.join("services", "converse_config.py"),
        f"{pkg}.services.converse_config",
        f"{pkg}.services",
    )
    activation_mod = _load(
        os.path.join("services", "activation.py"),
        f"{pkg}.services.activation",
        f"{pkg}.services",
    )
    audit_emitter_mod = _load(
        os.path.join("services", "audit_emitter.py"),
        f"{pkg}.services.audit_emitter",
        f"{pkg}.services",
    )
    turn_persistence_mod = _load(
        os.path.join("services", "turn_persistence.py"),
        f"{pkg}.services.turn_persistence",
        f"{pkg}.services",
    )
    memory_types_mod = _load(
        os.path.join("services", "memory", "types.py"),
        f"{pkg}.services.memory.types",
        f"{pkg}.services.memory",
    )
    memory_prov_mod = _load(
        os.path.join("services", "memory", "provenance.py"),
        f"{pkg}.services.memory.provenance",
        f"{pkg}.services.memory",
    )
    memory_context_mod = _load(
        os.path.join("services", "memory", "context.py"),
        f"{pkg}.services.memory.context",
        f"{pkg}.services.memory",
    )
    memory_wormhole_embed_mod = _load(
        os.path.join("services", "memory", "wormhole_embed.py"),
        f"{pkg}.services.memory.wormhole_embed",
        f"{pkg}.services.memory",
    )
    memory_graph_mod = _load(
        os.path.join("services", "memory", "graph.py"),
        f"{pkg}.services.memory.graph",
        f"{pkg}.services.memory",
    )
    memory_rem_synthesis_mod = _load(
        os.path.join("services", "memory", "rem_synthesis.py"),
        f"{pkg}.services.memory.rem_synthesis",
        f"{pkg}.services.memory",
    )
    memory_rem_mod = _load(
        os.path.join("services", "memory", "rem.py"),
        f"{pkg}.services.memory.rem",
        f"{pkg}.services.memory",
    )
    memory_query_mod = _load(
        os.path.join("services", "memory", "query.py"),
        f"{pkg}.services.memory.query",
        f"{pkg}.services.memory",
    )
    memory_asset_mod = _load(
        os.path.join("services", "memory", "asset.py"),
        f"{pkg}.services.memory.asset",
        f"{pkg}.services.memory",
    )
    memory_domain_mod = _load(
        os.path.join("services", "memory", "__init__.py"),
        f"{pkg}.services.memory",
        f"{pkg}.services.memory",
    )
    memory_recall_mod = _load(
        os.path.join("services", "memory_recall.py"),
        f"{pkg}.services.memory_recall",
        f"{pkg}.services",
    )
    negotiation_mod = _load(
        os.path.join("services", "negotiation.py"),
        f"{pkg}.services.negotiation",
        f"{pkg}.services",
    )
    converse_audit_mod = _load(
        os.path.join("services", "converse_audit.py"),
        f"{pkg}.services.converse_audit",
        f"{pkg}.services",
    )
    v2_handler_mod = _load(
        os.path.join("routes", "v2_handler.py"),
        f"{pkg}.routes.v2_handler",
        f"{pkg}.routes",
    )
    routes_registry_mod = _load(
        os.path.join("routes", "registry.py"),
        f"{pkg}.routes.registry",
        f"{pkg}.routes",
    )
    memory_nodes_mod = _load(
        os.path.join("services", "memory_nodes.py"),
        f"{pkg}.services.memory_nodes",
        f"{pkg}.services",
    )
    system_probe_mod = _load(
        os.path.join("services", "system_probe.py"),
        f"{pkg}.services.system_probe",
        f"{pkg}.services",
    )
    status_snapshot_mod = _load(
        os.path.join("services", "status_snapshot.py"),
        f"{pkg}.services.status_snapshot",
        f"{pkg}.services",
    )
    status_subsystems_mod = _load(
        os.path.join("services", "status_subsystems.py"),
        f"{pkg}.services.status_subsystems",
        f"{pkg}.services",
    )
    dashboard_status_mod = _load(
        os.path.join("services", "dashboard_status.py"),
        f"{pkg}.services.dashboard_status",
        f"{pkg}.services",
    )
    peers_status_mod = _load(
        os.path.join("services", "peers_status.py"),
        f"{pkg}.services.peers_status",
        f"{pkg}.services",
    )
    network_status_mod = _load(
        os.path.join("services", "network_status.py"),
        f"{pkg}.services.network_status",
        f"{pkg}.services",
    )
    resilience_status_mod = _load(
        os.path.join("services", "resilience_status.py"),
        f"{pkg}.services.resilience_status",
        f"{pkg}.services",
    )
    identity_status_mod = _load(
        os.path.join("services", "identity_status.py"),
        f"{pkg}.services.identity_status",
        f"{pkg}.services",
    )
    audit_chain_status_mod = _load(
        os.path.join("services", "audit_chain_status.py"),
        f"{pkg}.services.audit_chain_status",
        f"{pkg}.services",
    )
    api_auth_status_mod = _load(
        os.path.join("services", "api_auth_status.py"),
        f"{pkg}.services.api_auth_status",
        f"{pkg}.services",
    )
    consensus_status_mod = _load(
        os.path.join("services", "consensus_status.py"),
        f"{pkg}.services.consensus_status",
        f"{pkg}.services",
    )
    assets_status_mod = _load(
        os.path.join("services", "assets_status.py"),
        f"{pkg}.services.assets_status",
        f"{pkg}.services",
    )
    shadow_projection_mod = _load(
        os.path.join("services", "shadow_projection.py"),
        f"{pkg}.services.shadow_projection",
        f"{pkg}.services",
    )
    conflict_control_mod = _load(
        os.path.join("services", "conflict_control.py"),
        f"{pkg}.services.conflict_control",
        f"{pkg}.services",
    )
    pruning_control_mod = _load(
        os.path.join("services", "pruning_control.py"),
        f"{pkg}.services.pruning_control",
        f"{pkg}.services",
    )
    consensus_control_mod = _load(
        os.path.join("services", "consensus_control.py"),
        f"{pkg}.services.consensus_control",
        f"{pkg}.services",
    )
    consolidation_status_mod = _load(
        os.path.join("services", "consolidation_status.py"),
        f"{pkg}.services.consolidation_status",
        f"{pkg}.services",
    )
    replay_status_mod = _load(
        os.path.join("services", "replay_status.py"),
        f"{pkg}.services.replay_status",
        f"{pkg}.services",
    )
    awakening_status_mod = _load(
        os.path.join("services", "awakening_status.py"),
        f"{pkg}.services.awakening_status",
        f"{pkg}.services",
    )
    pruning_status_mod = _load(
        os.path.join("services", "pruning_status.py"),
        f"{pkg}.services.pruning_status",
        f"{pkg}.services",
    )
    entropy_status_mod = _load(
        os.path.join("services", "entropy_status.py"),
        f"{pkg}.services.entropy_status",
        f"{pkg}.services",
    )
    persistence_status_mod = _load(
        os.path.join("services", "persistence_status.py"),
        f"{pkg}.services.persistence_status",
        f"{pkg}.services",
    )
    negotiation_conflict_status_mod = _load(
        os.path.join("services", "negotiation_conflict_status.py"),
        f"{pkg}.services.negotiation_conflict_status",
        f"{pkg}.services",
    )
    reflection_status_mod = _load(
        os.path.join("services", "reflection_status.py"),
        f"{pkg}.services.reflection_status",
        f"{pkg}.services",
    )
    conflict_resolution_status_mod = _load(
        os.path.join("services", "conflict_resolution_status.py"),
        f"{pkg}.services.conflict_resolution_status",
        f"{pkg}.services",
    )
    status_bootstrap_mod = _load(
        os.path.join("services", "status_bootstrap.py"),
        f"{pkg}.services.status_bootstrap",
        f"{pkg}.services",
    )
    projection_register_mod = _load(
        os.path.join("services", "projection_register.py"),
        f"{pkg}.services.projection_register",
        f"{pkg}.services",
    )
    projection_ingest_mod = _load(
        os.path.join("services", "projection_ingest.py"),
        f"{pkg}.services.projection_ingest",
        f"{pkg}.services",
    )
    memory_control_mod = _load(
        os.path.join("services", "memory_control.py"),
        f"{pkg}.services.memory_control",
        f"{pkg}.services",
    )
    replay_control_mod = _load(
        os.path.join("services", "replay_control.py"),
        f"{pkg}.services.replay_control",
        f"{pkg}.services",
    )
    reflection_control_mod = _load(
        os.path.join("services", "reflection_control.py"),
        f"{pkg}.services.reflection_control",
        f"{pkg}.services",
    )
    rem_control_mod = _load(
        os.path.join("services", "rem_control.py"),
        f"{pkg}.services.rem_control",
        f"{pkg}.services",
    )
    peer_mesh_mod = _load(
        os.path.join("services", "peer_mesh.py"),
        f"{pkg}.services.peer_mesh",
        f"{pkg}.services",
    )
    asset_gateway_mod = _load(
        os.path.join("services", "asset_gateway.py"),
        f"{pkg}.services.asset_gateway",
        f"{pkg}.services",
    )
    asset_route_bootstrap_mod = _load(
        os.path.join("services", "asset_route_bootstrap.py"),
        f"{pkg}.services.asset_route_bootstrap",
        f"{pkg}.services",
    )
    system_status_routes_mod = _load(
        os.path.join("routes", "system_status.py"),
        f"{pkg}.routes.system_status",
        f"{pkg}.routes",
    )
    asset_routes_mod = _load(
        os.path.join("routes", "asset.py"),
        f"{pkg}.routes.asset",
        f"{pkg}.routes",
    )
    peer_routes_mod = _load(
        os.path.join("routes", "peer.py"),
        f"{pkg}.routes.peer",
        f"{pkg}.routes",
    )
    control_plane_mod = _load(
        os.path.join("services", "control_plane.py"),
        f"{pkg}.services.control_plane",
        f"{pkg}.services",
    )
    control_bootstrap_mod = _load(
        os.path.join("services", "control_bootstrap.py"),
        f"{pkg}.services.control_bootstrap",
        f"{pkg}.services",
    )
    control_routes_mod = _load(
        os.path.join("routes", "control.py"),
        f"{pkg}.routes.control",
        f"{pkg}.routes",
    )
    static_routes_mod = _load(
        os.path.join("routes", "static.py"),
        f"{pkg}.routes.static",
        f"{pkg}.routes",
    )
    gateway_intent_mod = _load(
        os.path.join("services", "gateway_intent.py"),
        f"{pkg}.services.gateway_intent",
        f"{pkg}.services",
    )
    project_control_mod = _load(
        os.path.join("services", "project_control.py"),
        f"{pkg}.services.project_control",
        f"{pkg}.services",
    )
    auth_gate_mod = _load(
        os.path.join("http", "auth_gate.py"),
        f"{pkg}.http.auth_gate",
        f"{pkg}.http",
    )
    multipart_mod = _load(os.path.join("utils", "multipart.py"), f"{pkg}.utils.multipart", f"{pkg}.utils")
    return state_mod, svc_mod, routes_mod, ingest_mod, ingest_routes_mod, converse_mod, converse_events_mod, converse_routes_mod, llm_mod, converse_thinking_mod, converse_speech_mod, converse_config_mod, activation_mod, audit_emitter_mod, turn_persistence_mod, memory_domain_mod, memory_wormhole_embed_mod, memory_graph_mod, memory_rem_synthesis_mod, memory_rem_mod, memory_asset_mod, memory_recall_mod, negotiation_mod, converse_audit_mod, v2_handler_mod, memory_nodes_mod, system_probe_mod, status_snapshot_mod, status_subsystems_mod, dashboard_status_mod, peers_status_mod, network_status_mod, resilience_status_mod, identity_status_mod, audit_chain_status_mod, api_auth_status_mod, consensus_status_mod, assets_status_mod, shadow_projection_mod, conflict_control_mod, pruning_control_mod, consensus_control_mod, consolidation_status_mod, replay_status_mod, awakening_status_mod, pruning_status_mod, entropy_status_mod, persistence_status_mod, negotiation_conflict_status_mod, reflection_status_mod, conflict_resolution_status_mod, status_bootstrap_mod, projection_register_mod, projection_ingest_mod, memory_control_mod, replay_control_mod, reflection_control_mod, rem_control_mod, peer_mesh_mod, asset_gateway_mod, asset_route_bootstrap_mod, system_status_routes_mod, asset_routes_mod, peer_routes_mod, control_plane_mod, control_bootstrap_mod, control_routes_mod, static_routes_mod, gateway_intent_mod, project_control_mod, auth_gate_mod, multipart_mod, routes_registry_mod

def _load_kernel_module(name, fname):
    import importlib.util as u
    # Phase 4 reducers use relative imports (e.g. "from kernel.state_snapshot import ...")
    # so we need src/ on sys.path for the dependency chain.
    src_dir = os.path.dirname(KERNEL_DIR)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    spec = u.spec_from_file_location(name, os.path.join(KERNEL_DIR, fname))
    m = u.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

def _load_core_module(name, fname):
    import importlib.util as u
    spec = u.spec_from_file_location(name, os.path.join(CORE_DIR, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def _load_api_module(name, fname):
    import importlib.util as u
    spec = u.spec_from_file_location(name, os.path.join(API_DIR, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def _load_network_module(name, fname):
    import importlib.util as u
    spec = u.spec_from_file_location(name, os.path.join(NETWORK_DIR, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

_obs_mod    = _load_kernel_module("observe_reducer",    "observe_reducer.py")
_cog_mod    = _load_kernel_module("cognize_reducer",    "cognize_reducer.py")
_dec_mod    = _load_kernel_module("decide_reducer",     "decide_reducer.py")
_spk_mod    = _load_kernel_module("speak_reducer",      "speak_reducer.py")
_sto_mod    = _load_kernel_module("store_reducer",      "store_reducer.py")
_rfl_mod    = _load_kernel_module("reflect_reducer",    "reflect_reducer.py")
_snp_mod    = _load_kernel_module("state_snapshot",     "state_snapshot.py")
_idp_mod    = _load_kernel_module("identity_position",  "identity_position.py")
_l2d_mod    = _load_kernel_module("l2_degradation_policy", "l2_degradation_policy.py")

observe_fn     = _obs_mod.observe_fn
cognize_fn     = _cog_mod.cognize_fn
decide_fn      = _dec_mod.decide_fn
speak_fn       = _spk_mod.speak_fn
store_fn       = _sto_mod.store_fn
reflect_fn     = _rfl_mod.reflect_fn
BlockStore     = _sto_mod.BlockStore
StateSnapshot  = _snp_mod.StateSnapshot
EmotionSnapshot = _snp_mod.EmotionSnapshot

# ── Cognitive Engine State ──────────────────────────────────────────────
_engine_state = {
    "active": True,
    "engine_initialized": True,
    "state": StateSnapshot(),
    "memory_store": BlockStore(),
    "trace": [],
    "gtbs_events": [],
    "runtime_logs": [],
    "token_traces": [],
    "current_iteration": 0,
    "model_registry": {},
    "started_at": time.time(),
    "activation": {
        "scores": {},  # node_id -> activation score (0..1)
        "wormhole_links": [],  # [{source, target, similarity, energy}]
    },
    "consolidation": {
        "last_activity_at": time.time(),
        "last_shallow_at": 0,
        "last_rem_at": 0,
        "rem_running": False,
        "total_pruned": 0,
        "total_facts": 0,
        "last_rem_report": None,
    },
    "runtime_flags": {},
    "cognitive_prune": {
        "ref_counts": {},
        "conflict_counts": {},
        "archived_block_ids": [],
        "knowledge_conclusions": [],
        "last_run_at": 0,
        "last_report": None,
        "total_archived": 0,
        "total_summarized": 0,
    },
    "projection": {
        "nodes": {},
        "links": [],
    },
    "active_project": {
        "project_id": "default",
        "name": "Default Project",
        "lifecycle_id": "",
        "locked": False,
        "locked_at": 0.0,
        "lock_session_id": "",
    },
    "conversation_scratch": {
        "session_id": "",
        "items": [],
        "updated_at": 0.0,
        "expires_at": 0.0,
    },
}

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")

(
    _gw_state_mod,
    _gw_models_mod,
    _gw_routes_mod,
    _gw_ingest_mod,
    _gw_ingest_routes_mod,
    _gw_converse_mod,
    _gw_converse_events_mod,
    _gw_converse_routes_mod,
    _gw_llm_mod,
    _gw_converse_thinking_mod,
    _gw_converse_speech_mod,
    _gw_converse_config_mod,
    _gw_activation_mod,
    _gw_audit_emitter_mod,
    _gw_turn_persistence_mod,
    _gw_memory_domain_mod,
    _gw_memory_wormhole_embed_mod,
    _gw_memory_graph_mod,
    _gw_memory_rem_synthesis_mod,
    _gw_memory_rem_mod,
    _gw_memory_asset_mod,
    _gw_memory_recall_mod,
    _gw_negotiation_mod,
    _gw_converse_audit_mod,
    _gw_v2_handler_mod,
    _gw_memory_nodes_mod,
    _gw_system_probe_mod,
    _gw_status_snapshot_mod,
    _gw_status_subsystems_mod,
    _gw_dashboard_status_mod,
    _gw_peers_status_mod,
    _gw_network_status_mod,
    _gw_resilience_status_mod,
    _gw_identity_status_mod,
    _gw_audit_chain_status_mod,
    _gw_api_auth_status_mod,
    _gw_consensus_status_mod,
    _gw_assets_status_mod,
    _gw_shadow_projection_mod,
    _gw_conflict_control_mod,
    _gw_pruning_control_mod,
    _gw_consensus_control_mod,
    _gw_consolidation_status_mod,
    _gw_replay_status_mod,
    _gw_awakening_status_mod,
    _gw_pruning_status_mod,
    _gw_entropy_status_mod,
    _gw_persistence_status_mod,
    _gw_negotiation_conflict_status_mod,
    _gw_reflection_status_mod,
    _gw_conflict_resolution_status_mod,
    _gw_status_bootstrap_mod,
    _gw_projection_register_mod,
    _gw_projection_ingest_mod,
    _gw_memory_control_mod,
    _gw_replay_control_mod,
    _gw_reflection_control_mod,
    _gw_rem_control_mod,
    _gw_peer_mesh_mod,
    _gw_asset_gateway_mod,
    _gw_asset_route_bootstrap_mod,
    _gw_system_status_routes_mod,
    _gw_asset_routes_mod,
    _gw_peer_routes_mod,
    _gw_control_plane_mod,
    _gw_control_bootstrap_mod,
    _gw_control_routes_mod,
    _gw_static_routes_mod,
    _gw_gateway_intent_mod,
    _gw_project_control_mod,
    _gw_auth_gate_mod,
    _gw_multipart_mod,
    _gw_routes_registry_mod,
) = _bootstrap_gateway_modules()
EngineStateManager = _gw_state_mod.EngineStateManager
ModelConfigService = _gw_models_mod.ModelConfigService
ModelsRouteHandler = _gw_routes_mod.ModelsRouteHandler
DocumentIngestService = _gw_ingest_mod.DocumentIngestService
IngestHooks = _gw_ingest_mod.IngestHooks
IngestRouteHandler = _gw_ingest_routes_mod.IngestRouteHandler
ConverseService = _gw_converse_mod.ConverseService
ConverseRouteHandler = _gw_converse_routes_mod.ConverseRouteHandler
ExternalLlmService = _gw_llm_mod.ExternalLlmService
LlmMessageHooks = _gw_llm_mod.LlmMessageHooks
speech_text = _gw_converse_speech_mod.speech_text
decision_intent = _gw_converse_speech_mod.decision_intent
ConverseConfigService = _gw_converse_config_mod.ConverseConfigService
ConverseConfigHooks = _gw_converse_config_mod.ConverseConfigHooks
ActivationService = _gw_activation_mod.ActivationService
ActivationHooks = _gw_activation_mod.ActivationHooks
TurnPersistenceService = _gw_turn_persistence_mod.TurnPersistenceService
TurnPersistenceHooks = _gw_turn_persistence_mod.TurnPersistenceHooks
AuditEmitter = _gw_audit_emitter_mod.AuditEmitter
AuditEmitterHooks = _gw_audit_emitter_mod.AuditEmitterHooks
MemoryRecallService = _gw_memory_recall_mod.MemoryRecallService
MemoryRecallHooks = _gw_memory_recall_mod.MemoryRecallHooks
MemoryContextService = _gw_memory_domain_mod.MemoryContextService
DefaultProvenancePort = _gw_memory_domain_mod.DefaultProvenancePort
CoreModuleProvenanceAdapter = _gw_memory_domain_mod.CoreModuleProvenanceAdapter
NegotiationService = _gw_negotiation_mod.NegotiationService
NegotiationHooks = _gw_negotiation_mod.NegotiationHooks
ConverseAuditService = _gw_converse_audit_mod.ConverseAuditService
create_v2_handler = _gw_v2_handler_mod.create_v2_handler
V2Bindings = _gw_v2_handler_mod.V2Bindings
MemoryNodeSpecService = _gw_memory_nodes_mod.MemoryNodeSpecService
MemoryNodeSpecHooks = _gw_memory_nodes_mod.MemoryNodeSpecHooks
MemoryGraphService = _gw_memory_graph_mod.MemoryGraphService
MemoryGraphHooks = _gw_memory_graph_mod.MemoryGraphHooks
MemoryGraphConfig = _gw_memory_graph_mod.MemoryGraphConfig
MemoryRemService = _gw_memory_rem_mod.MemoryRemService
MemoryRemHooks = _gw_memory_rem_mod.MemoryRemHooks
MemoryRemConfig = _gw_memory_rem_mod.MemoryRemConfig
RemConsolidationSynthesizer = _gw_memory_rem_synthesis_mod.RemConsolidationSynthesizer
RemConsolidationSynthesisHooks = _gw_memory_rem_synthesis_mod.RemConsolidationSynthesisHooks
MemoryAssetService = _gw_memory_asset_mod.MemoryAssetService
MemoryAssetHooks = _gw_memory_asset_mod.MemoryAssetHooks
WormholeEmbedder = _gw_memory_wormhole_embed_mod.WormholeEmbedder
WormholeEmbedderHooks = _gw_memory_wormhole_embed_mod.WormholeEmbedderHooks
SystemProbeService = _gw_system_probe_mod.SystemProbeService
StatusSnapshotService = _gw_status_snapshot_mod.StatusSnapshotService
StatusSubsystemsService = _gw_status_subsystems_mod.StatusSubsystemsService
DashboardStatusService = _gw_dashboard_status_mod.DashboardStatusService
DashboardStatusHooks = _gw_dashboard_status_mod.DashboardStatusHooks
PeersStatusService = _gw_peers_status_mod.PeersStatusService
PeersStatusHooks = _gw_peers_status_mod.PeersStatusHooks
NetworkStatusService = _gw_network_status_mod.NetworkStatusService
NetworkStatusHooks = _gw_network_status_mod.NetworkStatusHooks
ResilienceStatusService = _gw_resilience_status_mod.ResilienceStatusService
ResilienceStatusHooks = _gw_resilience_status_mod.ResilienceStatusHooks
IdentityStatusService = _gw_identity_status_mod.IdentityStatusService
IdentityStatusHooks = _gw_identity_status_mod.IdentityStatusHooks
AuditChainStatusService = _gw_audit_chain_status_mod.AuditChainStatusService
AuditChainStatusHooks = _gw_audit_chain_status_mod.AuditChainStatusHooks
ApiAuthStatusService = _gw_api_auth_status_mod.ApiAuthStatusService
ApiAuthStatusHooks = _gw_api_auth_status_mod.ApiAuthStatusHooks
ConsensusStatusService = _gw_consensus_status_mod.ConsensusStatusService
ConsensusStatusHooks = _gw_consensus_status_mod.ConsensusStatusHooks
AssetsStatusService = _gw_assets_status_mod.AssetsStatusService
AssetsStatusHooks = _gw_assets_status_mod.AssetsStatusHooks
ShadowProjectionService = _gw_shadow_projection_mod.ShadowProjectionService
ShadowProjectionHooks = _gw_shadow_projection_mod.ShadowProjectionHooks
ConflictControlService = _gw_conflict_control_mod.ConflictControlService
ConflictControlHooks = _gw_conflict_control_mod.ConflictControlHooks
PruningControlService = _gw_pruning_control_mod.PruningControlService
PruningControlHooks = _gw_pruning_control_mod.PruningControlHooks
ConsensusControlService = _gw_consensus_control_mod.ConsensusControlService
ConsensusControlHooks = _gw_consensus_control_mod.ConsensusControlHooks
ConsolidationStatusService = _gw_consolidation_status_mod.ConsolidationStatusService
ConsolidationStatusHooks = _gw_consolidation_status_mod.ConsolidationStatusHooks
ReplayStatusService = _gw_replay_status_mod.ReplayStatusService
ReplayStatusHooks = _gw_replay_status_mod.ReplayStatusHooks
AwakeningStatusService = _gw_awakening_status_mod.AwakeningStatusService
AwakeningStatusHooks = _gw_awakening_status_mod.AwakeningStatusHooks
PruningStatusService = _gw_pruning_status_mod.PruningStatusService
PruningStatusHooks = _gw_pruning_status_mod.PruningStatusHooks
EntropyStatusService = _gw_entropy_status_mod.EntropyStatusService
EntropyStatusHooks = _gw_entropy_status_mod.EntropyStatusHooks
PersistenceStatusService = _gw_persistence_status_mod.PersistenceStatusService
PersistenceStatusHooks = _gw_persistence_status_mod.PersistenceStatusHooks
NegotiationConflictStatusService = _gw_negotiation_conflict_status_mod.NegotiationConflictStatusService
NegotiationConflictStatusHooks = _gw_negotiation_conflict_status_mod.NegotiationConflictStatusHooks
ReflectionStatusService = _gw_reflection_status_mod.ReflectionStatusService
ReflectionStatusHooks = _gw_reflection_status_mod.ReflectionStatusHooks
ConflictResolutionStatusService = _gw_conflict_resolution_status_mod.ConflictResolutionStatusService
ConflictResolutionStatusHooks = _gw_conflict_resolution_status_mod.ConflictResolutionStatusHooks
build_status_services = _gw_status_bootstrap_mod.build_status_services
StatusBootstrapHooks = _gw_status_bootstrap_mod.StatusBootstrapHooks
ProjectionRegisterService = _gw_projection_register_mod.ProjectionRegisterService
ProjectionRegisterHooks = _gw_projection_register_mod.ProjectionRegisterHooks
ProjectionIngestService = _gw_projection_ingest_mod.ProjectionIngestService
ProjectionIngestHooks = _gw_projection_ingest_mod.ProjectionIngestHooks
MemoryControlService = _gw_memory_control_mod.MemoryControlService
MemoryControlHooks = _gw_memory_control_mod.MemoryControlHooks
ReplayControlService = _gw_replay_control_mod.ReplayControlService
ReplayControlHooks = _gw_replay_control_mod.ReplayControlHooks
ReflectionControlService = _gw_reflection_control_mod.ReflectionControlService
ReflectionControlHooks = _gw_reflection_control_mod.ReflectionControlHooks
RemControlService = _gw_rem_control_mod.RemControlService
RemControlHooks = _gw_rem_control_mod.RemControlHooks
PeerMeshService = _gw_peer_mesh_mod.PeerMeshService
PeerMeshHooks = _gw_peer_mesh_mod.PeerMeshHooks
AssetGatewayService = _gw_asset_gateway_mod.AssetGatewayService
AssetGatewayHooks = _gw_asset_gateway_mod.AssetGatewayHooks
build_asset_route_services = _gw_asset_route_bootstrap_mod.build_asset_route_services
AssetRouteBootstrapHooks = _gw_asset_route_bootstrap_mod.AssetRouteBootstrapHooks
AuthGate = _gw_auth_gate_mod.AuthGate
build_post_routes = _gw_routes_registry_mod.build_post_routes
build_put_routes = _gw_routes_registry_mod.build_put_routes
SystemStatusRouteHandler = _gw_system_status_routes_mod.SystemStatusRouteHandler
AssetRouteHandler = _gw_asset_routes_mod.AssetRouteHandler
PeerRouteHandler = _gw_peer_routes_mod.PeerRouteHandler
ControlRouteHandler = _gw_control_routes_mod.ControlRouteHandler
ControlPlaneService = _gw_control_plane_mod.ControlPlaneService
build_control_services = _gw_control_bootstrap_mod.build_control_services
ControlBootstrapHooks = _gw_control_bootstrap_mod.ControlBootstrapHooks
StaticRouteHandler = _gw_static_routes_mod.StaticRouteHandler
GatewayIntentService = _gw_gateway_intent_mod.GatewayIntentService
ProjectControlService = _gw_project_control_mod.ProjectControlService
ProjectControlHooks = _gw_project_control_mod.ProjectControlHooks
_pipeline_mod = _load_kernel_module("kernel.pipeline", "pipeline.py")
PipelineDeps = _pipeline_mod.PipelineDeps
CognitivePipeline = _pipeline_mod.CognitivePipeline
_state_manager = EngineStateManager(_engine_state)
_model_service = None
_models_routes = None
_ingest_service = None
_ingest_routes = None
_converse_service = None
_converse_routes = None
_llm_service = None
_converse_config = None
_provenance_port = None
_memory_context_service = None
_memory_graph_service = None
_memory_rem_service = None
_memory_asset_service = None
_activation_service = None
_turn_persistence_service = None
_memory_recall_service = None
_negotiation_service = None
_audit_emitter = None
_converse_audit_service = None
V2Handler = None
_memory_node_service = None
_system_probe_service = None
_status_snapshot_service = None
_status_subsystems_service = None
_dashboard_status_service = None
_peers_status_service = None
_network_status_service = None
_resilience_status_service = None
_identity_status_service = None
_audit_chain_status_service = None
_api_auth_status_service = None
_consensus_status_service = None
_assets_status_service = None
_shadow_projection_service = None
_conflict_control_service = None
_pruning_control_service = None
_consensus_control_service = None
_projection_register_service = None
_projection_ingest_service = None
_memory_control_service = None
_project_control_service = None
_replay_control_service = None
_reflection_control_service = None
_rem_control_service = None
_peer_mesh_service = None
_asset_gateway_service = None
_auth_gate = None
_status_routes = None
_expert_routes = None
_asset_routes = None
_peer_routes = None
_control_routes = None
_control_plane_service = None
_static_routes = None
_gateway_intent_service = None

# ── Spreading Activation with Temporal Decay (personal memory graph) ──
_ACTIVATION_DECAY = 0.8
_ACTIVATION_THRESHOLD = 0.4
_ACTIVATION_SPREAD_HOP1 = 0.5
_ACTIVATION_SPREAD_HOP2 = 0.2
_ACTIVATION_SEED_PULSE = 1.0
_ACTIVATION_MAX_SCORE = 1.0
_activation_lock = threading.Lock()

# ── Wormhole Protocol (semantic cosine bridges) ──
_WORMHOLE_SIM_THRESHOLD = float(os.environ.get("CNEXUS_WORMHOLE_SIM_THRESHOLD", "0.75"))
_WORMHOLE_ENERGY_COEFF = float(os.environ.get("CNEXUS_WORMHOLE_ENERGY_COEFF", "0.40"))
_WORMHOLE_MAX_LINKS = int(os.environ.get("CNEXUS_WORMHOLE_MAX_LINKS", "64"))
_WORMHOLE_MAX_COMPARE = int(os.environ.get("CNEXUS_WORMHOLE_MAX_COMPARE", "28"))
_wormhole_embedder = None

# ── Converse latency tuning ──
def _env_bool(name, default=True):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


_CNEXUS_FAST_CONVERSE = _env_bool("CNEXUS_FAST_CONVERSE", True)
_CNEXUS_STREAM_DEFAULT = _env_bool("CNEXUS_STREAM_CONVERSE", True)
_INJECT_LIMIT = max(0, int(os.environ.get("CNEXUS_INJECT_LIMIT", "2")))
_INJECT_DESC_MAX = max(0, int(os.environ.get("CNEXUS_INJECT_DESC_MAX", "80")))
_LLM_MAX_TOKENS = max(64, int(os.environ.get("CNEXUS_LLM_MAX_TOKENS", "1024")))
_OLLAMA_KEEP_ALIVE = os.environ.get("CNEXUS_OLLAMA_KEEP_ALIVE", "30m").strip()
_OLLAMA_REGISTRY_TTL = float(os.environ.get("CNEXUS_OLLAMA_PROBE_TTL", "30"))
_ollama_registry_cache = {"at": 0.0, "status": None}
_ollama_registry_lock = threading.Lock()

_CONVERSE_MODES = frozenset({"fast", "deep", "raw"})

# ── Multi-Modal & Code Intelligence ──
_CNEXUS_VISION_MODEL = os.environ.get("CNEXUS_VISION_MODEL", "llava")
_asset_processor = None
_asset_vector_index = None
_asset_peer_sync = None
_asset_push_queue = None
_clip_embedder = None

# ── Local JSON persistence (personal memory snapshot) ──
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_RUNTIME_DATA_DIR = os.path.join(
    os.environ.get("CNEXUS_DATA_DIR", os.path.join(_BASE_DIR, "data")),
    "runtime",
)
_compiled_runtime = None


def _boot_cnexus_runtime(*, force_recompile: bool = False):
    """BOOT: Constitution → Policy (compiled, not Memory)."""
    global _compiled_runtime
    from runtime.bootstrap import boot_runtime

    result = boot_runtime(
        _BASE_DIR,
        data_dir=_RUNTIME_DATA_DIR,
        force_recompile=force_recompile,
        identity_manager=_get_identity_manager(),
    )
    _compiled_runtime = result.get("compiled")
    status = dict(result.get("status") or {})
    system_prompt = str(result.get("system_prompt") or "")
    _engine_state["runtime"] = {"status": status, "system_prompt": system_prompt}
    return status


def _runtime_context_only() -> str:
    rt = _engine_state.get("runtime") or {}
    return str(rt.get("system_prompt") or "")


def _compose_llm_context(memory_context: str = "") -> str:
    from runtime.context import build_memory_layer_preamble
    from gateway.services.conversation_scratch import format_scratch_for_prompt, normalize_scratch, prune_scratch

    runtime = _runtime_context_only().strip()
    scratch = format_scratch_for_prompt(
        prune_scratch(normalize_scratch(_engine_state)),
        max_items=8,
    ).strip()
    mem = (memory_context or "").strip()
    if mem:
        mem = build_memory_layer_preamble() + "\n" + mem
    parts = [part for part in (runtime, scratch, mem) if part]
    return "\n\n---\n\n".join(parts)


_scp_plane = None


def _scp_enabled() -> bool:
    try:
        from semantic.scp import scp_enabled

        return scp_enabled()
    except Exception:
        return False


def _get_scp_plane():
    global _scp_plane
    if _scp_plane is None:
        from semantic.scp import SemanticControlPlane

        _scp_plane = SemanticControlPlane()
    return _scp_plane


def _scp_admit_turn(input_text: str, activation_context: str, profile: dict):
    from semantic.types import SCPRequest, TurnProfile

    scp = _get_scp_plane()
    budget = scp.load_budget_state()
    turn_profile = TurnProfile(
        thinking_mode=str(profile.get("thinking_mode") or "precision"),
        converse_mode=str(profile.get("mode") or profile.get("converse_mode") or "fast"),
        memory_scope=str(profile.get("memory_scope") or "local"),
        expert_mode=profile.get("expert_mode"),
        style_source=str(profile.get("expert_style_source") or profile.get("style_source") or "prompt"),
    )

    recall_candidates = []
    prompt_candidates = []
    fact_hits = 0
    if turn_profile.expert_mode:
        try:
            from plugins.expert_distill.producer import ExpertCandidateProducer, expert_distill_enabled

            if expert_distill_enabled():
                producer = ExpertCandidateProducer()
                recall_candidates, prompt_candidates, fact_hits = producer.produce(
                    list(_engine_state["memory_store"].blocks),
                    query=str(input_text or ""),
                    subject_id=str(turn_profile.expert_mode),
                    style_source=turn_profile.style_source,
                )
        except Exception:
            pass

    request = SCPRequest(
        query=str(input_text or ""),
        turn_profile=turn_profile,
        activation_context=str(activation_context or ""),
        recall_candidates=recall_candidates,
        prompt_candidates=prompt_candidates,
        budget_state=budget,
        compose_llm_context=_compose_llm_context,
        fact_hits=fact_hits,
    )
    response = scp.admit(request)
    _engine_state["semantic_budget"] = response.budget_state.to_dict()
    _engine_state["semantic_drift"] = {
        "triggers": list(response.observation.triggers),
        "dual_path_risk": bool(response.observation.dual_path_risk),
        "entanglement_score": float(response.observation.entanglement_score),
        "cross_path_overlap_ratio": float(response.observation.cross_path_overlap_ratio),
    }
    if response.correction is not None:
        _engine_state["semantic_budget_correction"] = {
            "trigger_id": response.correction.trigger_id,
            "level": response.correction.level,
            "style_source_override": response.correction.style_source_override,
        }
    return response


def _recompile_runtime(*, force: bool = False):
    return _boot_cnexus_runtime(force_recompile=force)

_PERSIST_DIR = os.environ.get("CNEXUS_DATA_DIR", os.path.join(_BASE_DIR, "data"))
_PERSIST_FILE = os.environ.get("CNEXUS_PERSIST_FILE", os.path.join(_PERSIST_DIR, "cnexus_personal_state.json"))
_PERSIST_VERSION = "2.0-personal-persist-v1"
_PERSIST_DEBOUNCE_SEC = float(os.environ.get("CNEXUS_PERSIST_DEBOUNCE", "1.5"))
_persist_lock = threading.Lock()
_persist_timer = None
_persist_meta = {"saved_at": None, "loaded_at": None}

# ── Ed25519 node identity (sovereign anchor) ──
_identity_lock = threading.Lock()
_identity_manager = None
_identity_optional = os.environ.get("CNEXUS_IDENTITY_DISABLE", "").lower() in ("1", "true", "yes")


def _identity_key_path():
    return os.environ.get("CNEXUS_IDENTITY_FILE", os.path.join(_PERSIST_DIR, "identity.key"))


def _get_identity_manager():
    global _identity_manager
    if _identity_optional:
        return None
    if _identity_manager is not None:
        return _identity_manager
    with _identity_lock:
        if _identity_manager is not None:
            return _identity_manager
        try:
            _id_mod = _load_core_module("identity_manager", "identity_manager.py")
            _identity_manager = _id_mod.IdentityManager(_identity_key_path())
        except Exception:
            _identity_manager = None
        return _identity_manager


def _sign_record(data: dict) -> dict | None:
    im = _get_identity_manager()
    if im is None:
        return None
    try:
        return im.sign_payload(data)
    except Exception:
        return None


def _verify_record(envelope: dict) -> bool:
    im = _get_identity_manager()
    if im is None or not isinstance(envelope, dict):
        return False
    pubkey = envelope.get("pubkey")
    if not pubkey:
        return False
    return im.verify_payload(envelope, pubkey)


def _install_signed_memory_store(ms):
    if getattr(ms, "_cnexus_identity_wrapped", False):
        return
    _orig_add = ms.add

    def add(block):
        wrapped = dict(block)
        data = dict(wrapped.get("data") or {})
        prov = _get_provenance()
        if prov and "provenance" not in data:
            data = prov.block_data_with_provenance(data, provenance=prov.PROVENANCE_LOCAL_FULL)
            wrapped["data"] = data
        signed = _sign_record(wrapped)
        if signed:
            wrapped["identity"] = signed
        result = _orig_add(wrapped)
        _audit_event(
            "memory.block",
            {
                "block_id": block.get("block_id"),
                "label": block.get("label"),
                "importance": block.get("importance"),
                "content_preview": str((block.get("data") or {}).get("content") or "")[:480],
                "keywords": (block.get("data") or {}).get("keywords") or [],
            },
        )
        return result

    ms.add = add
    ms._cnexus_identity_wrapped = True


def _identity_status():
    return _identity_status_service.build()


# ── Append-only hash-chained audit log ──
_audit_lock = threading.Lock()
_audit_log = None
_audit_optional = os.environ.get("CNEXUS_AUDIT_DISABLE", "").lower() in ("1", "true", "yes")
_audit_integrity = {"ok": True, "message": "not checked"}


def _audit_log_path():
    return os.environ.get("CNEXUS_AUDIT_LOG", os.path.join(_PERSIST_DIR, "audit.log"))


def _get_audit_log():
    global _audit_log
    if _audit_optional:
        return None
    if _audit_log is not None:
        return _audit_log
    with _audit_lock:
        if _audit_log is not None:
            return _audit_log
        try:
            _audit_mod = _load_core_module("audit_log", "audit_log.py")
            _audit_log = _audit_mod.AuditLog(_audit_log_path())
        except Exception:
            _audit_log = None
        return _audit_log


def _audit_event(event: str, data: dict):
    im = _get_identity_manager()
    audit = _get_audit_log()
    if im is None or audit is None:
        return None
    payload = {"event": event, **data}
    try:
        with _audit_lock:
            return audit.log(im, payload)
    except Exception:
        return None


def _verify_audit_integrity():
    global _audit_integrity
    im = _get_identity_manager()
    audit = _get_audit_log()
    if audit is None:
        _audit_integrity = {"ok": True, "message": "audit disabled"}
        return _audit_integrity
    ok, msg = audit.verify_integrity(im)
    _audit_integrity = {
        "ok": bool(ok),
        "message": msg,
        "entries": audit.entry_count(),
        "path": _audit_log_path(),
    }
    return _audit_integrity


def _audit_status():
    return _audit_chain_status_service.build()


_auth_middleware = None
_peer_trust = None
_provenance = None


def _get_auth_middleware():
    global _auth_middleware
    if _auth_middleware is not None:
        return _auth_middleware
    try:
        _auth_middleware = _load_api_module("middleware", "middleware.py")
    except Exception:
        _auth_middleware = False
    return _auth_middleware


def _get_peer_trust():
    global _peer_trust
    if _peer_trust is not None:
        return _peer_trust
    try:
        _peer_trust = _load_api_module("peer_trust", "peer_trust.py")
    except Exception:
        _peer_trust = False
    return _peer_trust


def _get_provenance():
    global _provenance
    if _provenance is not None:
        return _provenance
    try:
        _provenance = _load_core_module("provenance", "provenance.py")
    except Exception:
        _provenance = False
    return _provenance


def _cnexus_auth_deny(path: str, headers, body: dict, *, method: str = "POST"):
    """Return (error_dict, status) if request must be blocked, else None."""
    normalized = (path or "/").rstrip("/") or "/"
    if normalized == "/api/p2p/handshake":
        action = str((body or {}).get("action") or "HELLO").upper()
        if action in ("HELLO", "HANDSHAKE_HELLO", "CHALLENGE_REQUEST", "HANDSHAKE_INIT"):
            return None
        if action == "HANDSHAKE_RESPONSE":
            return None

    mw = _get_auth_middleware()
    if not mw:
        return None
    requires_auth = mw.path_requires_auth(path)
    pt = _get_peer_trust()
    if not requires_auth and pt and method.upper() == "GET":
        requires_auth = pt.is_asset_content_get(path, body)
    if not requires_auth:
        return None
    im = _get_identity_manager()
    if im is None:
        return None
    ok, err, status = mw.verify_cnexus_auth(headers, body, im, max_skew=mw.max_skew_seconds())
    if not ok:
        return err, status

    if pt:
        reg = _get_peer_registry()
        tok, terr, tstatus = pt.verify_inbound_peer_trust(path, headers, reg, method=method, body=body)
        if not tok:
            return terr, tstatus
    return None


_p2p_handler = None
_peer_registry = None
_gossip_sync = None
_negotiation_manager = None
_reputation_registry = None
_genesis_sync = None
_network_firewall = None
_dht_service = None
_connectivity_manager = None
_log_replay_engine = None
_state_reconstructor = None
_self_reflection_engine = None
_log_replay_lock = threading.Lock()
_awakening_lock = threading.Lock()
_awakening_state = {
    "phase": "idle",
    "label": "idle",
    "progress": 0.0,
    "message": "",
    "started_at": None,
    "completed_at": None,
    "alive": True,
}


def _reputation_registry_path():
    return os.environ.get("CNEXUS_REPUTATION_FILE", os.path.join(_PERSIST_DIR, "reputation.json"))


def _get_reputation_registry():
    global _reputation_registry
    if _reputation_registry is not None:
        return _reputation_registry
    try:
        rep_mod = _load_core_module("reputation_registry", "reputation_registry.py")
        _reputation_registry = rep_mod.ReputationRegistry(_reputation_registry_path())
    except Exception:
        _reputation_registry = None
    return _reputation_registry


def _negotiation_conflict_enabled():
    flags = _engine_state.get("runtime_flags") or {}
    if "negotiation_conflict_enabled" in flags:
        return bool(flags["negotiation_conflict_enabled"])
    raw = os.environ.get("CNEXUS_NEGOTIATION_CONFLICT")
    if raw is None:
        return True
    return raw.lower() not in ("0", "false", "no", "")


def _set_negotiation_conflict_enabled(enabled: bool) -> bool:
    flags = _engine_state.setdefault("runtime_flags", {})
    flags["negotiation_conflict_enabled"] = bool(enabled)
    return _negotiation_conflict_enabled()


def _negotiation_conflict_use_llm():
    flags = _engine_state.get("runtime_flags") or {}
    if "negotiation_conflict_llm" in flags:
        return bool(flags["negotiation_conflict_llm"])
    return os.environ.get("CNEXUS_NEGOTIATION_CONFLICT_LLM", "").lower() in ("1", "true", "yes")


def _set_negotiation_conflict_llm(enabled: bool) -> bool:
    flags = _engine_state.setdefault("runtime_flags", {})
    flags["negotiation_conflict_llm"] = bool(enabled)
    return _negotiation_conflict_use_llm()


def _handle_negotiation_failed(neg_result: dict, conflicts: list, peer_pubkey: str):
    if not _negotiation_conflict_enabled() or not conflicts:
        return
    resolutions = []
    pairs = []
    max_pairs = max(1, min(int(os.environ.get("CNEXUS_NEGOTIATION_CONFLICT_LIMIT", "3")), 8))
    use_llm = _negotiation_conflict_use_llm()
    for local_row, remote_row in conflicts[:max_pairs]:
        local_entry = {**local_row, "source": "local"}
        remote_entry = {
            **remote_row,
            "source": "remote",
            "source_peer": peer_pubkey,
        }
        report = _run_conflict_resolution(
            local_entry,
            remote_entry,
            mode="emergent",
            use_llm=use_llm,
            apply=False,
        )
        pair = {
            "block_id": str(local_row.get("block_id") or remote_row.get("block_id") or ""),
            "local": {
                "content": str(local_row.get("content") or ""),
                "label": str(local_row.get("label") or "episode"),
            },
            "remote": {
                "content": str(remote_row.get("content") or ""),
                "label": str(remote_row.get("label") or "episode"),
                "source_peer": str(peer_pubkey or remote_row.get("source_peer") or ""),
            },
            "resolution": None,
        }
        if report.get("ok") and report.get("status") in ("merged", "forked", "aligned"):
            resolutions.append(report)
            pair["resolution"] = {
                "status": report.get("status"),
                "merged_content": report.get("merged_content"),
                "fork": report.get("fork"),
                "rationale": report.get("rationale"),
                "source": report.get("source"),
                "temperature": report.get("temperature"),
                "global_entropy": report.get("global_entropy"),
                "entropy_seed": report.get("entropy_seed"),
            }
        else:
            pair["resolution"] = {"error": report.get("error") or "resolution_failed"}
        pairs.append(pair)
    if not pairs:
        return

    store = _get_entropy_store()
    peer_host = ""
    reg = _get_peer_registry()
    if reg and peer_pubkey:
        peer_meta = (reg.get_all_peers() or {}).get(str(peer_pubkey)) or {}
        peer_host = str(peer_meta.get("host") or "")
    buffer_row = {
        "id": f"neg-{int(time.time() * 1000)}",
        "peer_pubkey": str(peer_pubkey or "")[:64],
        "peer_host": peer_host,
        "negotiation_error": neg_result.get("error"),
        "negotiation_message": neg_result.get("message"),
        "global_entropy": store.global_entropy_hex(_get_peer_registry()) if store else None,
        "conflict_count": len(conflicts),
        "resolved_count": len(resolutions),
        "pairs": pairs,
        "resolutions": resolutions,
        "llm_used": use_llm,
        "at": time.time(),
    }
    buf = _engine_state.setdefault("negotiation_conflicts", [])
    buf.insert(0, buffer_row)
    if len(buf) > 8:
        del buf[8:]

    prune = _get_cognitive_pruning_engine()
    if prune:
        for local_row, remote_row in conflicts[:max_pairs]:
            block_id = str(local_row.get("block_id") or remote_row.get("block_id") or "")
            if block_id:
                prune.record_conflict_block(block_id)

    neg_result["conflict_audit_id"] = buffer_row["id"]
    neg_result["conflict_resolutions"] = [
        {
            "status": row.get("status"),
            "block_id": row.get("block_id"),
            "source": row.get("source"),
            "rationale": row.get("rationale"),
        }
        for row in resolutions
    ]
    _audit_event(
        "negotiation.conflict",
        {
            "peer_pubkey": str(peer_pubkey or "")[:64],
            "negotiation_error": neg_result.get("error"),
            "conflict_count": len(conflicts),
            "resolved_count": len(resolutions),
            "global_entropy": buffer_row.get("global_entropy"),
            "preview": _negotiation_conflict_context()[:480],
        },
    )
    _append_runtime_log(
        f"协商冲突消解 · {len(resolutions)}/{len(conflicts)} · peer={str(peer_pubkey or '')[:12]}",
        category="control_plane",
    )


def _negotiation_conflict_context() -> str:
    return _negotiation_service.conflict_context()


def _get_negotiation_manager():
    global _negotiation_manager
    if _negotiation_manager is not None:
        attach = getattr(_negotiation_manager, "attach_conflict_handler", None)
        if callable(attach):
            attach(_handle_negotiation_failed)
        return _negotiation_manager
    audit = _get_audit_log()
    im = _get_identity_manager()
    mw = _get_auth_middleware()
    if audit is None:
        return None
    try:
        consensus_mod = _load_core_module("consensus", "consensus.py")
        build_headers = mw.build_signed_headers if mw and im else None
        _negotiation_manager = consensus_mod.NegotiationManager(
            audit,
            im,
            _get_reputation_registry(),
            build_signed_headers=build_headers,
            on_negotiation_failed=_handle_negotiation_failed,
        )
    except Exception:
        _negotiation_manager = None
    if _negotiation_manager is not None:
        attach = getattr(_negotiation_manager, "attach_conflict_handler", None)
        if callable(attach):
            attach(_handle_negotiation_failed)
    return _negotiation_manager


def _peer_registry_path():
    return os.environ.get("CNEXUS_PEERS_FILE", os.path.join(_PERSIST_DIR, "peers.json"))


def _catalog_store_path():
    return os.environ.get("CNEXUS_CATALOG_FILE", os.path.join(_PERSIST_DIR, "catalog.json"))


_catalog_service = None
_cognitive_service = None
_storage_service = None
_repair_service = None
_application_service = None


def _load_catalog_module(name, fname):
    import importlib.util as u
    catalog_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "catalog")
    spec = u.spec_from_file_location(name, os.path.join(catalog_dir, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _get_catalog_service():
    global _catalog_service
    if _catalog_service is not None:
        return _catalog_service
    try:
        store_mod = _load_catalog_module("catalog_store", "store.py")
        service_mod = _load_catalog_module("catalog_service", "service.py")
        store = store_mod.CatalogStore(_catalog_store_path())
        _catalog_service = service_mod.CatalogService(store)
    except Exception:
        _catalog_service = None
    return _catalog_service


def _cognitive_store_path():
    return os.environ.get("CNEXUS_COGNITIVE_FILE", os.path.join(_PERSIST_DIR, "cognitive.json"))


def _load_cognitive_module(name, fname):
    import importlib.util as u
    cognitive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "cognitive")
    spec = u.spec_from_file_location(name, os.path.join(cognitive_dir, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _chunks_dir():
    return os.environ.get("CNEXUS_CHUNKS_DIR", os.path.join(_PERSIST_DIR, "chunks"))


def _descriptor_store_path():
    return os.environ.get("CNEXUS_DESCRIPTOR_FILE", os.path.join(_PERSIST_DIR, "chunk_descriptors.json"))


def _execution_policy_path():
    return os.environ.get("CNEXUS_EXECUTION_POLICY_FILE", os.path.join(_PERSIST_DIR, "execution_policy.json"))


def _get_storage_service():
    global _storage_service
    if _storage_service is not None:
        return _storage_service
    try:
        chunk_mod = _load_storage_module("storage_chunk_store", "chunk_store.py")
        manifest_mod = _load_storage_module("storage_manifest_store", "manifest_store.py")
        desc_mod = _load_storage_module("storage_descriptor_store", "descriptor_store.py")
        service_mod = _load_storage_module("storage_service", "service.py")
        chunk_store = chunk_mod.ChunkStore(_chunks_dir())
        manifest_store = manifest_mod.ManifestStore(_manifest_store_path())
        descriptor_store = desc_mod.DescriptorStore(_descriptor_store_path())
        _storage_service = service_mod.StorageService(chunk_store, manifest_store, descriptor_store)
    except Exception:
        _storage_service = None
    return _storage_service


def _get_repair_service():
    global _repair_service
    if _repair_service is not None:
        return _repair_service
    storage = _get_storage_service()
    if storage is None:
        return None
    try:
        repair_mod = _load_storage_module("storage_repair_service", "repair_service.py")
        policy_mod = _load_storage_module("storage_execution_policy_store", "execution_policy_store.py")
        _repair_service = repair_mod.RepairService(
            storage,
            catalog_service=_get_catalog_service(),
            policy_store=policy_mod.ExecutionPolicyStore(_execution_policy_path()),
        )
    except Exception:
        _repair_service = None
    return _repair_service


def _load_application_module(name, fname):
    import importlib.util as u
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "application")
    spec = u.spec_from_file_location(name, os.path.join(app_dir, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _get_application_service():
    global _application_service
    if _application_service is not None:
        return _application_service
    cognitive = _get_cognitive_service()
    if cognitive is None:
        return None
    try:
        facade_mod = _load_application_module("application_facade", "facade.py")
        _application_service = facade_mod.ApplicationFacade(
            cognitive=cognitive,
            catalog=_get_catalog_service(),
            storage=_get_storage_service(),
            repair_service=_get_repair_service(),
            memory_blocks=lambda: list(_engine_state["memory_store"].blocks),
            identity_pubkey=lambda: (_identity_status().get("pubkey") or ""),
            get_peer_registry=_get_peer_registry,
        )
    except Exception:
        _application_service = None
    return _application_service


def _bootstrap_share_local_memory():
    """Default ON — publish local BlockStore to catalog so peers can discover/repair."""
    try:
        share_mod = _load_application_module("application_share_boot", "share_boot.py")
        app = _get_application_service()
        identity = _identity_status()
        report = share_mod.bootstrap_share_local_memory(
            app,
            memory_blocks=list(_engine_state["memory_store"].blocks),
            identity_pubkey=str(identity.get("pubkey") or ""),
        )
        return report
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _get_cognitive_service():
    global _cognitive_service
    if _cognitive_service is not None:
        return _cognitive_service
    try:
        store_mod = _load_cognitive_module("cognitive_commit_store", "commit_store.py")
        service_mod = _load_cognitive_module("cognitive_service", "service.py")
        manifest_mod = _load_storage_module("storage_manifest_store", "manifest_store.py")
        txn_mod = _load_storage_module("storage_publish_txn", "publish_txn.py")
        chunk_mod = _load_storage_module("storage_chunk_store", "chunk_store.py")
        storage = _get_storage_service()
        store = store_mod.CommitStore(_cognitive_store_path())
        catalog = _get_catalog_service()
        manifest_store = manifest_mod.ManifestStore(_manifest_store_path())
        txn_store = txn_mod.PublishTxnStore(_publish_txn_path())
        chunk_store = chunk_mod.ChunkStore(_chunks_dir()) if storage is None else storage.chunks
        _cognitive_service = service_mod.CognitiveService(
            store,
            catalog_service=catalog,
            manifest_store=manifest_store,
            txn_store=txn_store,
            chunk_store=chunk_store,
            storage_service=storage,
        )
        txn_store.recover(_cognitive_service)
    except Exception:
        _cognitive_service = None
    return _cognitive_service


def _manifest_store_path():
    return os.environ.get("CNEXUS_MANIFEST_FILE", os.path.join(_PERSIST_DIR, "manifests.json"))


def _publish_txn_path():
    return os.environ.get("CNEXUS_PUBLISH_TXN_FILE", os.path.join(_PERSIST_DIR, "publish_txn.json"))


def _load_storage_module(name, fname):
    import importlib.util as u
    storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "storage")
    spec = u.spec_from_file_location(name, os.path.join(storage_dir, fname))
    m = u.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _bind_host():
    try:
        host_mod = _load_network_module("host_config", "host_config.py")
        return host_mod.resolve_bind_host()
    except Exception:
        return os.environ.get("CNEXUS_BIND_HOST", "0.0.0.0")


def _public_url():
    try:
        host_mod = _load_network_module("host_config", "host_config.py")
        port = int(os.environ.get("CNEXUS_PORT", "7864"))
        return host_mod.resolve_public_url(port)
    except Exception:
        return str(os.environ.get("CNEXUS_PUBLIC_URL", "") or "").strip()


def _local_peer_host():
    cm = _get_connectivity_manager()
    if cm is not None:
        url = str(getattr(cm, "public_url", "") or "").strip()
        if url:
            return url if url.startswith(("http://", "https://")) else f"http://{url}"
    port = int(os.environ.get("CNEXUS_PORT", "7864"))
    return f"http://{_bind_host()}:{port}"


def _dht_http_post(host: str, payload: dict) -> dict:
    host = str(host or "").strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        f"{host}/api/dht/rpc",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _get_network_firewall():
    global _network_firewall
    if _network_firewall is not None:
        return _network_firewall
    try:
        fw_mod = _load_network_module("network_firewall", "network_firewall.py")
        _network_firewall = fw_mod.NetworkFirewall(
            _get_reputation_registry(),
            audit_fn=_audit_event,
        )
    except Exception:
        _network_firewall = None
    return _network_firewall


def _get_dht_service():
    global _dht_service
    if _dht_service is not None:
        return _dht_service
    im = _get_identity_manager()
    if im is None:
        return None
    try:
        dht_mod = _load_network_module("dht_service", "dht_service.py")
        _dht_service = dht_mod.DHTService(
            im.public_key_hex(),
            peer_registry=_get_peer_registry(),
            http_post=_dht_http_post,
        )
        _dht_service.seed_from_registry()
    except Exception:
        _dht_service = None
    return _dht_service


def _get_connectivity_manager():
    global _connectivity_manager
    if _connectivity_manager is not None:
        return _connectivity_manager
    im = _get_identity_manager()
    if im is None:
        return None
    try:
        cm_mod = _load_network_module("connectivity_manager", "connectivity_manager.py")
        stun_mod = _load_network_module("stun_client", "stun_client.py")
        port = int(os.environ.get("CNEXUS_PORT", "7864"))
        _connectivity_manager = cm_mod.ConnectivityManager(
            local_pubkey=im.public_key_hex(),
            local_port=port,
            bind_host=_bind_host(),
            public_url=_public_url(),
            dht_service=_get_dht_service(),
            peer_registry=_get_peer_registry(),
            network_firewall=_get_network_firewall(),
            stun_gather_fn=stun_mod.gather_srflx_candidate,
        )
    except Exception:
        _connectivity_manager = None
    return _connectivity_manager


def _network_status():
    return _network_status_service.build()


def _perform_outbound_handshake(url, peer_id, handler, local_host):
    client_mod = _load_network_module("p2p_handshake_client", "p2p_handshake_client.py")
    return client_mod.perform_outbound_handshake(url, peer_id, handler, local_host=local_host)


def _start_network_stack():
    cm = _get_connectivity_manager()
    dht = _get_dht_service()
    gossip = _get_gossip_sync()
    fw = _get_network_firewall()
    if cm:
        cm.gather_candidates(refresh_stun=True)
        cm.start_worker(interval=float(os.environ.get("CNEXUS_CONNECTIVITY_POLL", "120")))
    if dht and cm:
        endpoints = [str(c.get("url") or "") for c in (cm.status().get("candidates") or []) if c.get("url")]
        port = int(os.environ.get("CNEXUS_PORT", "7864"))
        announce_host = cm.public_url or _public_url() or f"http://127.0.0.1:{port}"
        dht.announce(announce_host, endpoints=endpoints)
        dht.bootstrap()
        _seed_dht_from_lan(dht, port)
    if gossip and cm:
        gossip.attach_connectivity(cm, fw)


def _seed_dht_from_lan(dht, port: int):
    try:
        host_mod = _load_network_module("host_config", "host_config.py")
        lan_mod = _load_network_module("lan_discovery", "lan_discovery.py")
    except Exception:
        return
    if not host_mod.lan_discovery_enabled():
        return

    def _worker():
        try:
            for row in lan_mod.scan_lan_cnexus_nodes(port=port, timeout=0.25):
                pubkey = str(row.get("pubkey") or "")
                host = str(row.get("host") or row.get("url") or "")
                if pubkey and host and hasattr(dht, "_touch_node"):
                    dht._touch_node(pubkey, host, endpoints=[host])
        except Exception:
            pass

    threading.Thread(target=_worker, name="cnexus-lan-seed", daemon=True).start()


def _get_peer_registry():
    global _peer_registry
    if _peer_registry is not None:
        return _peer_registry
    try:
        reg_mod = _load_core_module("peer_registry", "peer_registry.py")
        _peer_registry = reg_mod.PeerRegistry(_peer_registry_path())
    except Exception:
        _peer_registry = None
    return _peer_registry


def _get_p2p_handler():
    global _p2p_handler
    im = _get_identity_manager()
    if im is None:
        return None
    if _p2p_handler is not None:
        return _p2p_handler
    try:
        p2p_mod = _load_api_module("p2p_handler", "p2p_handler.py")
        _p2p_handler = p2p_mod.HandshakeHandler(im)
    except Exception:
        _p2p_handler = None
    return _p2p_handler


def _get_gossip_sync():
    global _gossip_sync
    if _gossip_sync is not None:
        return _gossip_sync
    audit = _get_audit_log()
    im = _get_identity_manager()
    mw = _get_auth_middleware()
    if audit is None:
        return None
    try:
        gossip_mod = _load_network_module("gossip_sync", "gossip_sync.py")
        build_headers = mw.build_signed_headers if mw and im else None
        _gossip_sync = gossip_mod.GossipSync(audit, im, build_headers)
        reg = _get_peer_registry()
        if reg is not None:
            _gossip_sync.attach_peer_registry(reg)
        neg = _get_negotiation_manager()
        if neg is not None:
            _gossip_sync.attach_negotiation(neg)
        global _genesis_sync
        if _genesis_sync is None:
            try:
                genesis_mod = _load_network_module("genesis_sync", "genesis_sync.py")
                _genesis_sync = genesis_mod.GenesisSync(
                    _gossip_sync,
                    on_aligned=_on_genesis_aligned,
                )
                _gossip_sync.attach_genesis(_genesis_sync)
                store = _get_entropy_store()
                if store:
                    _genesis_sync.attach_entropy(store)
            except Exception:
                _genesis_sync = None
    except Exception:
        _gossip_sync = None
    return _gossip_sync


def _snapshot_dir():
    return os.environ.get("CNEXUS_SNAPSHOT_DIR", os.path.join(_PERSIST_DIR, "snapshots"))


def _awakening_update(**fields):
    with _awakening_lock:
        _awakening_state.update(fields)


def _awakening_from_reconstructor(recon):
    if recon is None:
        return
    progress = dict(recon.progress or {})
    phase = str(progress.get("phase") or "idle")
    _awakening_update(
        phase=phase,
        label=phase,
        progress=float(progress.get("progress") or 0.0),
        message=str(progress.get("message") or ""),
        started_at=progress.get("started_at"),
        completed_at=progress.get("completed_at"),
        alive=phase in ("alive", "idle"),
    )


def _read_awakening_base() -> dict:
    with _awakening_lock:
        return dict(_awakening_state)


def _genesis_status() -> dict:
    genesis = _get_genesis_sync()
    return genesis.status() if genesis else {}


def _reconstructor_status() -> dict:
    recon = _get_state_reconstructor()
    return recon.status() if recon else {}


def _awakening_status() -> dict:
    return _status_subsystems_service.awakening_status()


def _get_state_reconstructor():
    global _state_reconstructor
    if _state_reconstructor is not None:
        return _state_reconstructor
    audit = _get_audit_log()
    replay = _get_log_replay_engine()
    if audit is None or replay is None:
        return None
    try:
        recon_mod = _load_core_module("state_reconstructor", "state_reconstructor.py")
        _state_reconstructor = recon_mod.StateReconstructor(
            audit,
            replay,
            _snapshot_dir(),
        )
    except Exception:
        _state_reconstructor = None
    return _state_reconstructor


def _get_self_reflection_engine():
    global _self_reflection_engine
    if _self_reflection_engine is not None:
        return _self_reflection_engine
    audit = _get_audit_log()
    if audit is None:
        return None
    try:
        reflect_mod = _load_core_module("self_reflection", "self_reflection.py")
        _self_reflection_engine = reflect_mod.SelfReflectionEngine(
            audit,
            vector_index=_get_asset_vector_index(),
            audit_fn=_audit_event,
        )
    except Exception:
        _self_reflection_engine = None
    return _self_reflection_engine


def _invoke_reflection_llm(system_prompt: str, user_prompt: str) -> str:
    model_row = _model_service.resolve_model_row_for_chat(_model_service.active_model_id())
    if not model_row or not ExternalLlmService.should_use_external(model_row):
        return ""
    return _llm_service.invoke_with_messages(
        model_row,
        ExternalLlmService.build_simple_messages(system_prompt, user_prompt),
        mode_profile={"inject_memory": False},
    )["reply"]


def _reflection_engine_status():
    engine = _get_self_reflection_engine()
    if engine is None:
        return {"enabled": False}
    return engine.status()


def _reflection_status():
    return _status_subsystems_service.reflection_status()


def _run_self_reflection(
    *,
    question: str | None = None,
    limit: int | None = None,
    window_days: int | None = None,
    use_llm: bool = True,
) -> dict:
    engine = _get_self_reflection_engine()
    if engine is None:
        return {"ok": False, "error": "reflection_unavailable"}
    report = engine.reflect(
        question=question,
        limit=limit,
        window_days=window_days,
        use_llm=use_llm,
        llm_fn=_invoke_reflection_llm if use_llm else None,
    )
    if report.get("ok"):
        preview = str(report.get("reflection") or "")[:240]
        _append_runtime_log(f"元认知反思 · {preview}", category="control_plane")
        ms = _engine_state["memory_store"]
        ms.blocks.append({
            "block_id": f"meta-reflect-{int(time.time())}",
            "label": "reflective",
            "data": {
                "content": str(report.get("reflection") or "")[:2000],
                "question": report.get("question"),
                "source": report.get("source"),
                "biases": report.get("biases"),
                "metacognitive": True,
            },
            "importance": 0.78,
            "timestamp": time.time(),
        })
        _schedule_persist()
    return report


_conflict_agent = None
_entropy_store = None


def _entropy_file_path():
    return os.environ.get("CNEXUS_ENTROPY_FILE", os.path.join(_PERSIST_DIR, "entropy.json"))


def _get_entropy_store():
    global _entropy_store
    if _entropy_store is not None:
        return _entropy_store
    try:
        mod = _load_core_module("entropy", "entropy.py")
        if not mod.entropy_sync_enabled():
            _entropy_store = False
            return _entropy_store
        _entropy_store = mod.EntropyStore(_entropy_file_path())
    except Exception:
        _entropy_store = False
    return _entropy_store


def _entropy_status():
    return _status_subsystems_service.entropy_status()


def _global_entropy_int() -> int:
    store = _get_entropy_store()
    if not store:
        return 0
    return int(store.global_entropy(_get_peer_registry()))


def _get_conflict_agent():
    global _conflict_agent
    if _conflict_agent is not None:
        return _conflict_agent
    try:
        mod = _load_core_module("conflict_resolution", "conflict_resolution.py")
        _conflict_agent = mod.ConflictResolutionAgent()
    except Exception:
        _conflict_agent = False
    return _conflict_agent


def _conflict_resolution_enabled():
    agent = _get_conflict_agent()
    if not agent:
        return False
    try:
        return bool(agent.status().get("enabled"))
    except Exception:
        return False


def _invoke_emergent_llm(system_prompt: str, user_prompt: str, temperature: float) -> str:
    model_row = _model_service.resolve_model_row_for_chat(_model_service.active_model_id())
    if not model_row or not ExternalLlmService.should_use_external(model_row):
        return ""
    temp = max(0.0, min(float(temperature or 0.7), 1.5))
    return _llm_service.invoke_with_messages(
        model_row,
        ExternalLlmService.build_simple_messages(system_prompt, user_prompt),
        mode_profile={
            "inject_memory": False,
            "llm_max_tokens": min(_LLM_MAX_TOKENS, 2048),
            "temperature": temp,
        },
    )["reply"]


def _trusted_peer_pubkeys() -> list[str]:
    reg = _get_peer_registry()
    if reg is None:
        return []
    rows = reg.get_all_peers()
    return [
        pubkey
        for pubkey, row in rows.items()
        if str(row.get("status") or "").strip() in ("trusted", "online")
    ]


def _apply_conflict_resolution_to_store(block_id: str, resolution: dict) -> bool:
    block_id = str(block_id or "").strip()
    if not block_id or not resolution.get("ok"):
        return False
    mod = _get_conflict_agent()
    if not mod:
        return False
    ms = _engine_state["memory_store"]
    for index, block in enumerate(ms.blocks):
        if str(block.get("block_id") or "") != block_id:
            continue
        ms.blocks[index] = mod.apply_resolution_to_block(block, resolution)
        _schedule_persist()
        return True
    return False


def _run_conflict_resolution(
    local_entry: dict,
    remote_entry: dict,
    *,
    mode: str = "emergent",
    use_llm: bool = True,
    apply: bool = False,
    seed: int | None = None,
) -> dict:
    agent = _get_conflict_agent()
    if not agent:
        return {"ok": False, "error": "conflict_resolution_unavailable"}
    if not _conflict_resolution_enabled():
        return {"ok": False, "error": "conflict_resolution_disabled"}

    llm_fn = None
    if use_llm and mode == "emergent":
        llm_fn = _invoke_emergent_llm

    report = agent.resolve(
        local_entry,
        remote_entry,
        mode=mode,
        seed=seed if seed is not None else _global_entropy_int(),
        use_llm=use_llm,
        llm_fn=llm_fn,
    )
    store = _get_entropy_store()
    if store:
        report["global_entropy"] = store.global_entropy_hex(_get_peer_registry())
    block_id = str(local_entry.get("block_id") or remote_entry.get("block_id") or "")
    if apply and report.get("ok") and report.get("status") in ("merged", "forked") and block_id:
        applied = _apply_conflict_resolution_to_store(block_id, report)
        report["applied"] = applied
        if applied:
            canonical = str(report.get("merged_content") or "").strip()
            if report.get("status") == "forked":
                fork = dict(report.get("fork") or {})
                canonical = f"{fork.get('local', '')} {fork.get('remote', '')}".strip()
            _audit_event(
                "conflict.resolve",
                {
                    "block_id": block_id,
                    "status": report.get("status"),
                    "mode": report.get("mode"),
                    "source": report.get("source"),
                    "entropy_seed": report.get("entropy_seed"),
                    "temperature": report.get("temperature"),
                    "rationale": str(report.get("rationale") or "")[:480],
                    "content_preview": canonical[:480],
                },
            )
            _append_runtime_log(
                f"冲突消解 · {report.get('status')} · {block_id[:16]}",
                category="control_plane",
            )
    return report


def _replay_conflict_handler(existing_block: dict, incoming_data: dict, ts: float) -> dict:
    mod = _get_conflict_agent()
    if not mod or not _conflict_resolution_enabled():
        return {"applied": False, "reason": "disabled"}
    local_entry = mod.entry_from_block(existing_block, source="local")
    remote_entry = mod.entry_from_audit_data(incoming_data, source="remote")
    report = _run_conflict_resolution(
        local_entry,
        remote_entry,
        mode="precision",
        use_llm=False,
        apply=True,
    )
    canonical = ""
    if report.get("status") == "merged":
        canonical = str(report.get("merged_content") or "")
    elif report.get("status") == "forked":
        fork = dict(report.get("fork") or {})
        canonical = f"{fork.get('local', '')} {fork.get('remote', '')}".strip()
    return {
        "applied": bool(report.get("applied")),
        "canonical_content": canonical,
        "resolution": report,
    }


def _conflict_agent_status():
    agent = _get_conflict_agent()
    return agent.status() if agent else {"enabled": False}


def _conflict_resolution_status():
    return _status_subsystems_service.conflict_resolution_status()


_cognitive_pruning_engine = None


def _prune_archive_dir():
    return os.environ.get("CNEXUS_PRUNE_ARCHIVE_DIR", os.path.join(_PERSIST_DIR, "prune_archive"))


def _get_cognitive_pruning_engine():
    global _cognitive_pruning_engine
    if _cognitive_pruning_engine is not None:
        return _cognitive_pruning_engine
    try:
        prune_mod = _load_core_module("cognitive_pruning", "cognitive_pruning.py")
        _cognitive_pruning_engine = prune_mod.CognitivePruningEngine(
            _engine_state,
            _engine_state["memory_store"],
            archive_dir=_prune_archive_dir(),
            audit_fn=_audit_event,
        )
    except Exception:
        _cognitive_pruning_engine = None
    return _cognitive_pruning_engine


def _pruning_status():
    return _status_subsystems_service.pruning_status()


def _record_emergent_block_refs():
    _negotiation_service.record_emergent_block_refs()


def _negotiation_conflict_recent():
    return _status_subsystems_service.negotiation_conflict_recent()


def _get_log_replay_engine():
    global _log_replay_engine
    if _log_replay_engine is not None:
        return _log_replay_engine
    audit = _get_audit_log()
    if audit is None:
        return None
    try:
        replay_mod = _load_core_module("log_replay", "log_replay.py")
        handler = _replay_conflict_handler if _conflict_resolution_enabled() else None
        _log_replay_engine = replay_mod.LogReplayEngine(audit, conflict_handler=handler)
    except Exception:
        _log_replay_engine = None
    return _log_replay_engine


def _replay_status():
    return _status_subsystems_service.replay_status()


def _run_log_replay(*, force: bool = False, reset: bool = True) -> dict:
    with _log_replay_lock:
        replay_mod = _load_core_module("log_replay", "log_replay.py")
        if not replay_mod.replay_enabled():
            return {"ok": False, "error": "replay_disabled"}

        engine = _get_log_replay_engine()
        audit = _get_audit_log()
        recon = _get_state_reconstructor()
        if engine is None or audit is None:
            return {"ok": False, "error": "replay_unavailable"}

        counts = engine.count_replayable_events()
        replayable = sum(
            counts.get(k, 0) for k in ("memory.block", "trace.cycle", "asset.upload", "asset.received")
        )
        ms = _engine_state["memory_store"]
        needed = engine.replay_needed(
            audit_entry_count=audit.entry_count(),
            memory_block_count=len(ms.blocks),
            trace_count=len(_engine_state.get("trace", [])),
            replayable_in_audit=replayable,
        )
        if not force and not needed:
            return {"ok": True, "skipped": True, "reason": "replay_not_needed", "status": _replay_status()}

        _awakening_update(
            phase="replay",
            label="replay",
            progress=0.05,
            message="记忆重塑启动…",
            started_at=time.time(),
            completed_at=None,
            alive=False,
        )

        def _reindex_assets():
            proc = _get_asset_processor()
            idx = _get_asset_vector_index()
            if proc is None or idx is None:
                return {"ok": False, "error": "asset_index_unavailable"}

            def _read_blob(asset_id: str, meta: dict):
                blob, _, _ = proc.read_raw(asset_id)
                return blob

            return idx.rebuild_all(proc.list_assets(limit=500), read_blob_fn=_read_blob)

        if recon is not None:
            report = recon.reconstruct(
                memory_store=ms,
                engine_state=_engine_state,
                reputation_registry=_get_reputation_registry(),
                force=force,
                reset=reset,
                reindex_assets=_reindex_assets,
            )
            _awakening_from_reconstructor(recon)
        else:
            report = engine.replay(
                memory_store=ms,
                engine_state=_engine_state,
                reset=reset,
                keep_models=True,
            )
            _awakening_update(phase="alive", label="alive", progress=1.0, message="回放完成", alive=True, completed_at=time.time())

        if report.get("ok"):
            _schedule_persist()
            summary = report.get("summary") or (
                f"Log replay · blocks={report.get('memory_blocks')} "
                f"trace={report.get('trace_rows')} assets={report.get('assets_indexed')}"
            )
            _append_runtime_log(summary, category="control_plane")
            _awakening_update(message=summary, alive=True, phase="alive", label="alive", progress=1.0, completed_at=time.time())
        return report


def _maybe_replay_on_boot():
    try:
        replay_mod = _load_core_module("log_replay", "log_replay.py")
        if not replay_mod.replay_on_boot():
            return
    except Exception:
        return
    _run_log_replay(force=False, reset=True)


def _on_genesis_aligned(result: dict):
    try:
        replay_mod = _load_core_module("log_replay", "log_replay.py")
        if not replay_mod.replay_after_genesis():
            return
    except Exception:
        return
    if not result.get("ok"):
        return
    merged = int((result.get("full_log") or {}).get("merged_total") or 0)
    aligned = bool(result.get("aligned"))
    if aligned or merged > 0:
        _awakening_update(
            phase="genesis",
            label="genesis",
            progress=0.85,
            message=f"基因同步完成 · merged={merged}",
            alive=False,
        )
        threading.Thread(
            target=lambda: _run_log_replay(force=True, reset=False),
            daemon=True,
            name="cnexus-log-replay",
        ).start()


def _get_genesis_sync():
    global _genesis_sync
    if _gossip_sync is None:
        _get_gossip_sync()
    return _genesis_sync


def _peers_status():
    return _peers_status_service.build()


def _consensus_status():
    return _consensus_status_service.build()


_metrics_module = None
_SERVER_PORT = 7864
_peer_heartbeat_started = False


def _get_metrics_module():
    global _metrics_module
    if _metrics_module is not None:
        return _metrics_module
    try:
        _metrics_module = _load_api_module("metrics", "metrics.py")
    except Exception:
        _metrics_module = False
    return _metrics_module


def _heartbeat_stale_seconds():
    try:
        return int(os.environ.get("CNEXUS_PEER_STALE_SECONDS", "120"))
    except ValueError:
        return 120


def _heartbeat_interval():
    try:
        return int(os.environ.get("CNEXUS_HEARTBEAT_INTERVAL", "30"))
    except ValueError:
        return 30


def _start_peer_heartbeat():
    global _peer_heartbeat_started
    if _peer_heartbeat_started:
        return
    if os.environ.get("CNEXUS_HEARTBEAT_DISABLE", "").lower() in ("1", "true", "yes"):
        return
    gossip = _get_gossip_sync()
    reg = _get_peer_registry()
    if gossip is None:
        return
    gossip.attach_peer_registry(reg)
    gossip.start_heartbeat_loop(reg, interval=_heartbeat_interval())
    gossip.schedule_genesis_bootstrap()
    genesis = _get_genesis_sync()
    if genesis and getattr(genesis, "enabled", False):
        _awakening_update(
            phase="genesis",
            label="genesis",
            progress=0.08,
            message="基因同步 (Genesis Handshake) 启动…",
            started_at=time.time(),
            alive=False,
        )
    _start_asset_push_retry()
    _start_network_stack()
    _peer_heartbeat_started = True


def _api_auth_status():
    return _api_auth_status_service.build()


def _default_model_registry():
    return ModelConfigService.default_registry(OLLAMA_HOST)


_engine_state["model_registry"] = _default_model_registry()


def _persist_file_path():
    os.makedirs(_PERSIST_DIR, exist_ok=True)
    return _PERSIST_FILE


def _state_snapshot_to_dict(st):
    if not isinstance(st, StateSnapshot):
        return {}
    return {
        "emotion": {
            "val": st.emotion.val,
            "arousal": st.emotion.arousal,
            "dominance": st.emotion.dominance,
        },
        "relationship": dict(st.relationship or {}),
        "goal": dict(st.goal or {}),
        "attention": dict(st.attention or {}),
        "meta": dict(st.meta or {}),
    }


def _state_snapshot_from_dict(data):
    data = data or {}
    em = data.get("emotion") or {}
    return StateSnapshot(
        emotion=EmotionSnapshot(
            val=float(em.get("val", 0.0)),
            arousal=float(em.get("arousal", 0.5)),
            dominance=float(em.get("dominance", 0.5)),
        ),
        relationship=dict(data.get("relationship") or {}),
        goal=dict(data.get("goal") or {}),
        attention=dict(data.get("attention") or {}),
        meta=dict(data.get("meta") or {}),
    )


def _to_jsonable(obj, depth=0):
    if depth > 10:
        return str(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, StateSnapshot):
        return _state_snapshot_to_dict(obj)
    if isinstance(obj, EmotionSnapshot):
        return {
            "val": obj.val,
            "arousal": obj.arousal,
            "dominance": obj.dominance,
        }
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v, depth + 1) for v in obj]
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return _to_jsonable(vars(obj), depth + 1)
    return str(obj)


def _serialize_engine_state():
    es = _engine_state
    return {
        "persist_version": _PERSIST_VERSION,
        "saved_at": time.time(),
        "current_iteration": int(es.get("current_iteration", 0)),
        "started_at": float(es.get("started_at", time.time())),
        "state": _state_snapshot_to_dict(es["state"]),
        "memory_blocks": _to_jsonable(es["memory_store"].blocks),
        "trace": _to_jsonable(es.get("trace", [])[-120:]),
        "activation": _to_jsonable(es.get("activation", {})),
        "projection": _to_jsonable(es.get("projection", {"nodes": {}, "links": []})),
        "consolidation": _to_jsonable(es.get("consolidation", {})),
        "cognitive_prune": _to_jsonable(es.get("cognitive_prune", {})),
        "runtime_flags": _to_jsonable(es.get("runtime_flags", {})),
        "gtbs_events": _to_jsonable(es.get("gtbs_events", [])[-500:]),
        "runtime_logs": _to_jsonable(es.get("runtime_logs", [])[-200:]),
        "token_traces": _to_jsonable(es.get("token_traces", [])[-20:]),
        "model_registry": _to_jsonable(es.get("model_registry", {})),
        "active_project": _to_jsonable(es.get("active_project", {})),
        "conversation_scratch": _to_jsonable(es.get("conversation_scratch", {})),
    }


def _apply_persisted_state(payload):
    if not isinstance(payload, dict) or payload.get("persist_version") != _PERSIST_VERSION:
        return False
    es = _engine_state
    es["state"] = _state_snapshot_from_dict(payload.get("state"))
    es["current_iteration"] = int(payload.get("current_iteration", 0))
    es["started_at"] = float(payload.get("started_at", time.time()))
    blocks = payload.get("memory_blocks") or []
    es["memory_store"].blocks = list(blocks) if isinstance(blocks, list) else []
    es["trace"] = list(payload.get("trace") or [])
    act = payload.get("activation") or {}
    es["activation"] = {
        "scores": dict(act.get("scores") or {}),
        "wormhole_links": list(act.get("wormhole_links") or []),
    }
    proj = payload.get("projection") or {}
    es["projection"] = {
        "nodes": dict(proj.get("nodes") or {}),
        "links": list(proj.get("links") or []),
    }
    cons = dict(es.get("consolidation") or {})
    cons.update(payload.get("consolidation") or {})
    cons["rem_running"] = False
    es["consolidation"] = cons
    if isinstance(payload.get("cognitive_prune"), dict):
        es["cognitive_prune"] = dict(payload.get("cognitive_prune") or {})
    if isinstance(payload.get("runtime_flags"), dict):
        es["runtime_flags"] = dict(payload.get("runtime_flags") or {})
    saved_reg = payload.get("model_registry") or {}
    merged = _default_model_registry()
    if isinstance(saved_reg, dict):
        merged.update(saved_reg)
    es["model_registry"] = merged
    es["gtbs_events"] = list(payload.get("gtbs_events") or [])
    es["runtime_logs"] = list(payload.get("runtime_logs") or [])
    es["token_traces"] = list(payload.get("token_traces") or [])
    if isinstance(payload.get("active_project"), dict):
        from gateway.services.memory.project import normalize_active_project

        es["active_project"] = normalize_active_project(payload.get("active_project"))
    if isinstance(payload.get("conversation_scratch"), dict):
        from gateway.services.conversation_scratch import default_scratch_state

        scratch = default_scratch_state()
        scratch.update(payload.get("conversation_scratch") or {})
        es["conversation_scratch"] = scratch
    return True


def _atomic_write_json(path, payload, *, compact: bool = False):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".cnexus-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            if compact:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            else:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _cancel_scheduled_persist():
    global _persist_timer
    with _persist_lock:
        if _persist_timer is not None:
            _persist_timer.cancel()
            _persist_timer = None


def _persist_engine_state(*, audit_checkpoint: bool = True):
    with _persist_lock:
        try:
            payload = _serialize_engine_state()
            path = _persist_file_path()
            _atomic_write_json(path, payload)
            _persist_meta["saved_at"] = payload["saved_at"]
            if audit_checkpoint:
                audit = _get_audit_log()
                if audit is not None:
                    _audit_event(
                        "state.checkpoint",
                        {
                            "memory_blocks": len(_engine_state["memory_store"].blocks),
                            "trace_count": len(_engine_state.get("trace", [])),
                            "iteration": int(_engine_state.get("current_iteration", 0)),
                            "audit_head": audit.last_hash,
                        },
                    )
            return True
        except Exception as exc:
            _append_runtime_log(f"持久化失败 · {exc}", category="control_plane", level="error")
            return False


def _persist_engine_state_fast():
    """Post-clear snapshot — compact JSON, no checkpoint audit (memory.clear already logged)."""
    with _persist_lock:
        try:
            payload = _serialize_engine_state()
            path = _persist_file_path()
            _atomic_write_json(path, payload, compact=True)
            _persist_meta["saved_at"] = payload["saved_at"]
            return True
        except Exception as exc:
            _append_runtime_log(f"持久化失败 · {exc}", category="control_plane", level="error")
            return False


def _schedule_persist():
    global _persist_timer

    def _fire():
        _persist_engine_state()

    with _persist_lock:
        if _persist_timer is not None:
            _persist_timer.cancel()
        _persist_timer = threading.Timer(_PERSIST_DEBOUNCE_SEC, _fire)
        _persist_timer.daemon = True
        _persist_timer.start()


def _init_model_gateway():
    global _model_service, _models_routes
    _model_service = ModelConfigService(
        _state_manager,
        schedule_persist=_schedule_persist,
        ollama_host=OLLAMA_HOST,
        ollama_registry_ttl=_OLLAMA_REGISTRY_TTL,
    )
    _models_routes = ModelsRouteHandler(_model_service)


_init_model_gateway()


def _load_engine_state_on_boot():
    path = _persist_file_path()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not _apply_persisted_state(payload):
            return False
        _persist_meta["loaded_at"] = time.time()
        _persist_meta["saved_at"] = payload.get("saved_at")
        _append_runtime_log(
            (
                f"记忆快照恢复 · blocks={len(_engine_state['memory_store'].blocks)} "
                f"trace={len(_engine_state.get('trace', []))} "
                f"iteration={_engine_state.get('current_iteration', 0)}"
            ),
            category="control_plane",
        )
        return True
    except Exception as exc:
        _append_runtime_log(f"快照加载失败 · {exc}", category="control_plane", level="warn")
        return False


def _persistence_status():
    return _status_subsystems_service.persistence_status()


def _reset_engine_memory(model_registry=None, *, preserve_constitution=True):
    protected_blocks = []
    if preserve_constitution:
        try:
            from gateway.services.memory.protection import clone_protected_block, is_clear_protected
        except ImportError:
            from cnexus_gateway.services.memory.protection import clone_protected_block, is_clear_protected
        store = _engine_state.get("memory_store")
        if store is not None:
            protected_blocks = [
                clone_protected_block(block)
                for block in store.blocks
                if is_clear_protected(block)
            ]

    es = _engine_state
    es["state"] = StateSnapshot()
    es["memory_store"] = BlockStore()
    es["trace"] = []
    es["gtbs_events"] = []
    es["runtime_logs"] = []
    es["token_traces"] = []
    es["current_iteration"] = 0
    es["activation"] = {"scores": {}, "wormhole_links": []}
    es["projection"] = {"nodes": {}, "links": []}
    now = time.time()
    es["consolidation"] = {
        "last_activity_at": now,
        "last_shallow_at": 0,
        "last_rem_at": 0,
        "rem_running": False,
        "total_pruned": 0,
        "total_facts": 0,
        "last_rem_report": None,
    }
    if model_registry is not None:
        es["model_registry"] = model_registry
    if protected_blocks:
        for block in protected_blocks:
            es["memory_store"].add(block)
        _append_runtime_log(
            f"记忆清空 · 保留认知宪法 {len(protected_blocks)} 条",
            category="control_plane",
        )


def _iso_ts():
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())


def _gtbs_row(phase, tx_id, trace_id, kind, entry, caller="http", mutability="explicit", shadow=False, extra=None):
    row = {
        "event_type": phase,
        "transaction_id": tx_id,
        "ts": _iso_ts(),
        "payload": {
            "write_intent_kind": kind,
            "mutability": mutability,
            "provenance": {
                "trace_id": trace_id,
                "caller": caller,
                "channel": "cnexus-2.0-personal",
                "entry_registry": entry,
            },
            "phase": phase,
        },
    }
    if shadow:
        row["payload"]["shadow"] = True
        row["payload"]["gtbs_mode"] = "SHADOW"
    if extra:
        row["payload"].update(extra)
    return row


def _append_runtime_log(message, category="gtbs", level="info", trace_id=None):
    entry = {
        "id": f"log-{int(time.time()*1000)}-{len(_engine_state['runtime_logs'])}",
        "timestamp": _iso_ts(),
        "level": level,
        "category": category,
        "message": message,
        "meta": {"trace_id": trace_id} if trace_id else {},
    }
    _engine_state["runtime_logs"].append(entry)
    if len(_engine_state["runtime_logs"]) > 500:
        _engine_state["runtime_logs"] = _engine_state["runtime_logs"][-500:]


def _record_flow_logs(iteration, trace_id, input_text, decision):
    """Emit categorized runtime logs that drive the 7-layer Neural Flow model."""
    preview = (input_text or "").strip()[:80]
    intent = _decision_intent(decision)
    _append_runtime_log(f"感官输入 · {preview or '(empty)'}", category="chat", trace_id=trace_id)
    _append_runtime_log(f"执行链激活 · intent={intent}", category="execution", trace_id=trace_id)
    _append_runtime_log("记忆写入 episodic/emotion", category="capture", trace_id=trace_id)
    _append_runtime_log(f"认知脉冲 #{iteration} · CSE trace", category="cse", trace_id=trace_id)


def _record_cycle_gtbs(iteration, trace_id, input_text, decision, speech, store_result):
    """Project one 6-step cognitive cycle into GTBS-compatible debugger events."""
    it = iteration
    preview = (input_text or "").strip()[:80]
    rows = [
        _gtbs_row("proposal", f"tx-{it}-dispatch", trace_id, "chat_dispatch", "process_interaction"),
        _gtbs_row(
            "proposal", f"tx-{it}-observe", trace_id, "observe", "observe_fn",
            caller="internal", mutability="implicit", shadow=True,
            extra={"reason": preview or "empty input"},
        ),
        _gtbs_row(
            "proposal", f"tx-{it}-cognize", trace_id, "cognize", "cognize_fn",
            caller="internal", mutability="implicit", shadow=True,
        ),
        _gtbs_row(
            "proposal", f"tx-{it}-decide", trace_id, "decide", "decide_fn",
            caller="internal", mutability="advisory",
            extra={"intent": (decision or {}).get("intent", "converse")},
        ),
        _gtbs_row(
            "commit", f"tx-{it}-speak", trace_id, "chat", "speak_fn",
            extra={"reply_preview": str((speech or {}).get("text", ""))[:120]},
        ),
        _gtbs_row(
            "commit", f"tx-{it}-store", trace_id, "capture", "store_fn",
            extra={
                "target_stores": ["episodic", "emotion"],
                "blocks_written": (store_result or {}).get("blocks_written", {}),
            },
        ),
        _gtbs_row(
            "proposal", f"tx-{it}-reflect", trace_id, "reflect", "reflect_fn",
            caller="internal", mutability="advisory", shadow=True,
        ),
    ]
    _engine_state["gtbs_events"].extend(rows)
    if len(_engine_state["gtbs_events"]) > 2000:
        _engine_state["gtbs_events"] = _engine_state["gtbs_events"][-2000:]
    _append_runtime_log(
        f"6-step cycle #{it} · intent={(decision or {}).get('intent', 'converse')} · input={preview or '(empty)'}",
        category="gtbs",
        trace_id=trace_id,
    )
    _record_flow_logs(it, trace_id, input_text, decision)


def _seed_boot_events():
    if _engine_state["gtbs_events"]:
        return
    trace_id = "v2-boot-0"
    boot_rows = [
        _gtbs_row("proposal", "tx-boot-1", trace_id, "system_boot", "kernel_boot", caller="internal", mutability="advisory"),
        _gtbs_row("commit", "tx-boot-2", trace_id, "runtime_ready", "gateway_health", caller="internal"),
    ]
    _engine_state["gtbs_events"].extend(boot_rows)
    _append_runtime_log("CNexus 2.0 personal kernel online", category="control_plane", trace_id=trace_id)


_seed_boot_events()

def _resolve_model_row(model_id=None):
    return _model_service.resolve_model_row(model_id)


def _resolve_model_row_for_chat(model_id=None):
    return _model_service.resolve_model_row_for_chat(model_id)


def _llm_chat_url(model_row):
    return ExternalLlmService.chat_url(model_row)


def _ollama_chat_options(profile=None):
    return _llm_service.ollama_chat_options(profile)


def _init_converse_config():
    global _converse_config
    _converse_config = ConverseConfigService(
        activation_threshold=_ACTIVATION_THRESHOLD,
        inject_limit=_INJECT_LIMIT,
        inject_desc_max=_INJECT_DESC_MAX,
        llm_max_tokens=_LLM_MAX_TOKENS,
        converse_modes=_CONVERSE_MODES,
        hooks=ConverseConfigHooks(global_entropy_int=_global_entropy_int),
    )


def _normalize_converse_mode(raw):
    return _converse_config.normalize_converse_mode(raw)


def _converse_mode_profile(mode):
    return _converse_config.converse_mode_profile(mode)


def _normalize_thinking_mode(raw):
    return _converse_config.normalize_thinking_mode(raw)


def _thinking_inference_params(thinking_mode="precision"):
    return _converse_config.thinking_inference_params(thinking_mode)


def _parse_converse_request_modes(data: dict | None):
    return _converse_config.parse_request_modes(data)


def _init_memory_domain_gateway():
    global _provenance_port, _memory_context_service
    core = _get_provenance()
    if core and core is not False:
        _provenance_port = CoreModuleProvenanceAdapter(core)
    else:
        _provenance_port = DefaultProvenancePort()
    _memory_context_service = MemoryContextService(
        _provenance_port,
        default_desc_max=_INJECT_DESC_MAX,
    )


def _init_llm_gateway():
    global _llm_service
    _llm_service = ExternalLlmService(
        llm_max_tokens=_LLM_MAX_TOKENS,
        ollama_keep_alive=_OLLAMA_KEEP_ALIVE,
        message_hooks=LlmMessageHooks(
            global_entropy_int=_global_entropy_int,
        ),
        provenance=_provenance_port,
        default_mode_profile=lambda: _converse_config.converse_mode_profile("fast"),
    )


_init_converse_config()
_init_memory_domain_gateway()
_init_llm_gateway()


def _sse_event(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _iter_converse_sse(input_text: str, model_id=None, converse_mode="fast", thinking_mode="precision"):
    yield from _converse_routes.iter_sse_strings(
        input_text,
        model_id=model_id,
        converse_mode=converse_mode,
        thinking_mode=thinking_mode,
    )


def _run_6step(input_text: str, model_id=None, converse_mode="fast", thinking_mode="precision") -> dict:
    """Run a full 6-step cognitive cycle, matching Phase 4 reducer signatures."""
    return _converse_service.run_blocking(
        input_text,
        model_id=model_id,
        converse_mode=converse_mode,
        thinking_mode=thinking_mode,
    )


def _init_audit_emitter_gateway():
    global _audit_emitter
    _audit_emitter = AuditEmitter(AuditEmitterHooks(audit_event=_audit_event))


def _store_fn_guarded(response, state, iteration_meta, block_store):
    result = store_fn(response, state, iteration_meta, block_store)
    if _scp_enabled():
        try:
            from semantic.anti_loop import apply_antiloop_after_store

            apply_antiloop_after_store(
                block_store,
                _engine_state.get("semantic_turn"),
                iteration_meta,
            )
        except Exception:
            pass
    return result


def _init_turn_persistence_gateway():
    global _turn_persistence_service
    from gateway.services.conversation_scratch import append_scratch_turn

    _turn_persistence_service = TurnPersistenceService(
        _state_manager,
        TurnPersistenceHooks(
            store=_store_fn_guarded,
            reflect=reflect_fn,
            sign_record=_sign_record,
            record_cycle_gtbs=_record_cycle_gtbs,
            schedule_activation_post_turn=_schedule_activation_post_turn,
            record_token_trace=_record_token_trace,
            schedule_persist=_schedule_persist,
            append_scratch_turn=lambda session_id, user_text, assistant_text, trace_id="": append_scratch_turn(
                _state_manager.mutate,
                session_id=session_id or "",
                user_text=user_text,
                assistant_text=assistant_text,
                trace_id=trace_id,
            ),
        ),
        _audit_emitter,
    )


def _init_memory_recall_gateway():
    global _memory_recall_service
    _memory_recall_service = MemoryRecallService(
        _state_manager,
        MemoryRecallHooks(get_cognitive_pruning_engine=_get_cognitive_pruning_engine),
        provenance=_provenance_port,
        context=_memory_context_service,
    )


def _init_negotiation_gateway():
    global _negotiation_service
    _negotiation_service = NegotiationService(
        _state_manager,
        NegotiationHooks(get_cognitive_pruning_engine=_get_cognitive_pruning_engine),
    )


def _init_converse_audit_gateway():
    global _converse_audit_service
    _converse_audit_service = ConverseAuditService(_audit_emitter)


def _init_converse_gateway():
    global _converse_service, _converse_routes
    deps = PipelineDeps(
        observe=observe_fn,
        cognize=cognize_fn,
        decide=decide_fn,
        speak=speak_fn,
        converse_mode_profile=_converse_config.converse_mode_profile,
        thinking_params=_converse_config.thinking_inference_params,
        touch_activity=_state_manager.touch_consolidation_activity,
        resolve_model=_model_service.resolve_model_row_for_chat,
        threshold_activated_fragments=_threshold_activated_fragments,
        format_activation_context=_memory_context_service.format_activation_context,
        compose_llm_context=_compose_llm_context,
        runtime_context=_runtime_context_only,
        memory_recall=_memory_recall_scoped,
        negotiation_conflict_context=_negotiation_service.conflict_context,
        record_emergent_block_refs=_negotiation_service.record_emergent_block_refs,
        should_use_external_llm=_llm_service.should_use_external_for_chat,
        iter_external_llm_stream=_llm_service.iter_stream,
        invoke_external_llm=_llm_service.invoke,
        audit_thinking=_converse_audit_service.audit_thinking,
        speech_text=speech_text,
        persist_turn=_turn_persistence_service.commit_turn,
        fast_converse=_CNEXUS_FAST_CONVERSE,
        scp_admit=_scp_admit_turn if _scp_enabled() else None,
    )
    pipeline = CognitivePipeline(_state_manager, deps)
    _converse_service = ConverseService(_state_manager, pipeline)
    _converse_routes = ConverseRouteHandler(
        _converse_service,
        _converse_config,
        stream_default=_CNEXUS_STREAM_DEFAULT,
    )


# ── HTTP Server ─────────────────────────────────────────────────────────
def _resilience_status():
    return _resilience_status_service.build()


def _normalize_memory_tag(label):
    return _gw_memory_nodes_mod.default_normalize_memory_tag(label)


def _extract_keywords(text, limit=6):
    if not text:
        return []
    import re
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", str(text))
    seen = set()
    out = []
    for tok in tokens:
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok[:24])
        if len(out) >= limit:
            break
    return out


def _activation_scores():
    return _engine_state.setdefault("activation", {}).setdefault("scores", {})


def _sync_activation_nodes(specs):
    _activation_service.sync_nodes(specs)


def _memory_items_for_overview():
    return _activation_service.overview_items()


def _projection_store():
    return _engine_state.setdefault("projection", {"nodes": {}, "links": []})


def _build_activation_adjacency(specs):
    return _memory_graph_service.build_adjacency(specs, _engine_state)


def _collect_memory_node_specs():
    return _memory_graph_service.collect()


def _memory_recall_scoped(query: str, memory_scope: str = "local") -> dict:
    from cnexus_gateway.services.memory.scope import normalize_memory_scope
    from cnexus_gateway.services.memory.types import QueryFilters

    return _memory_recall_service.recall(
        query,
        filters=QueryFilters(
            scope=normalize_memory_scope(memory_scope),
            trusted_peers=frozenset(_trusted_peer_pubkeys()),
        ),
    )


def _threshold_activated_fragments(limit=None, threshold=None, memory_scope="local", **kwargs):
    return _activation_service.threshold_activated_fragments(
        limit,
        threshold,
        memory_scope=memory_scope,
        trusted_peers=_trusted_peer_pubkeys(),
    )


def _format_activation_context(hits, desc_max=None):
    return _memory_context_service.format_activation_context(hits, desc_max)


def _init_memory_graph_gateway():
    global _memory_graph_service, _memory_node_service, _wormhole_embedder
    _wormhole_embedder = WormholeEmbedder(
        WormholeEmbedderHooks(
            append_runtime_log=_append_runtime_log,
            ollama_base_url=_ollama_base_url,
            probe_ollama=_probe_ollama,
        )
    )
    graph_config = MemoryGraphConfig(
        activation_decay=_ACTIVATION_DECAY,
        activation_threshold=_ACTIVATION_THRESHOLD,
        spread_hop1=_ACTIVATION_SPREAD_HOP1,
        spread_hop2=_ACTIVATION_SPREAD_HOP2,
        seed_pulse=_ACTIVATION_SEED_PULSE,
        max_score=_ACTIVATION_MAX_SCORE,
        wormhole_sim_threshold=_WORMHOLE_SIM_THRESHOLD,
        wormhole_energy_coeff=_WORMHOLE_ENERGY_COEFF,
        wormhole_max_links=_WORMHOLE_MAX_LINKS,
        wormhole_max_compare=_WORMHOLE_MAX_COMPARE,
    )
    _memory_graph_service = MemoryGraphService(
        _state_manager,
        MemoryGraphHooks(
            extract_keywords=_extract_keywords,
            append_runtime_log=_append_runtime_log,
            schedule_persist=_schedule_persist,
            background_cognitive_update=_background_cognitive_update,
        ),
        provenance=_provenance_port,
        embedder=_wormhole_embedder,
        config=graph_config,
        activation_lock=_activation_lock,
    )
    _memory_node_service = _memory_graph_service


def _init_memory_rem_gateway():
    global _memory_rem_service
    _memory_rem_service = MemoryRemService(
        _state_manager,
        _memory_graph_service,
        MemoryRemHooks(
            get_rem_engine=_get_rem_engine,
            extract_keywords=_extract_keywords,
            speech_text=speech_text,
            append_runtime_log=_append_runtime_log,
            schedule_persist=_schedule_persist,
            get_cognitive_pruning_engine=_get_cognitive_pruning_engine,
        ),
        RemConsolidationSynthesizer(
            RemConsolidationSynthesisHooks(
                extract_keywords=_extract_keywords,
                resolve_model_row=_resolve_model_row_for_chat,
                llm_invoke=lambda model_row, prompt: _llm_service.invoke(
                    model_row,
                    prompt,
                    memory_context=None,
                ),
            ),
        ),
        config=MemoryRemConfig(
            activation_threshold=_ACTIVATION_THRESHOLD,
            activation_max_score=_ACTIVATION_MAX_SCORE,
        ),
    )


def _init_activation_gateway():
    global _activation_service
    _activation_service = ActivationService(
        _state_manager,
        ActivationHooks(
            collect_node_specs=_memory_graph_service.collect,
        ),
        default_threshold=_ACTIVATION_THRESHOLD,
        default_inject_limit=_INJECT_LIMIT,
    )


def _match_seed_node_ids(text, specs):
    return _memory_graph_service.match_seed_ids(text, specs)


def _get_embedding_with_fallback(text):
    embedder = _wormhole_embedder or WormholeEmbedder()
    return embedder.embed(text)


def _schedule_activation_post_turn(user_text, reply, trace_id):
    _memory_graph_service.schedule_post_turn(user_text, reply, trace_id)


def _schedule_projection_wormhole(node_ids):
    _memory_graph_service.schedule_projection_wormhole(node_ids)


def _consolidation_state():
    return _engine_state.setdefault("consolidation", {})


def _init_ingest_gateway():
    global _ingest_service, _ingest_routes
    hooks = IngestHooks(
        touch_activity=_state_manager.touch_consolidation_activity,
        append_log=_append_runtime_log,
        gtbs_row=_gtbs_row,
        schedule_persist=_schedule_persist,
    )
    assets_dir = os.environ.get("CNEXUS_ASSETS_DIR", os.path.join(_PERSIST_DIR, "assets"))
    _ingest_service = DocumentIngestService(_state_manager, hooks, assets_dir=assets_dir)
    _ingest_routes = IngestRouteHandler(_ingest_service)


_init_ingest_gateway()


_rem_engine = None


def _get_rem_engine():
    global _rem_engine
    if _rem_engine is not None:
        return _rem_engine
    try:
        rem_mod = _load_core_module("rem_sleep", "rem_sleep.py")
        _rem_engine = rem_mod.RemSleepEngine(
            _engine_state["memory_store"],
            _get_audit_log(),
            _get_identity_manager(),
            audit_fn=_audit_event,
        )
    except Exception:
        _rem_engine = None
    return _rem_engine


def _consolidation_status():
    return _status_subsystems_service.consolidation_status()


def _background_cognitive_update():
    """浅度睡眠：对话后轻量代谢，不阻塞主链。"""
    try:
        c = _consolidation_state()
        c["last_shallow_at"] = time.time()
        trace = _engine_state.get("trace", [])
        if len(trace) > 40:
            _engine_state["trace"] = trace[-35:]
        _memory_graph_service.prune_stale_activation_scores()
        if len(_engine_state.get("gtbs_events", [])) > 1500:
            _engine_state["gtbs_events"] = _engine_state["gtbs_events"][-1500:]
    except Exception:
        pass


def _start_rem_watchdog():
    _memory_rem_service.start_watchdog()


# ── Multi-Modal Ingestion & Code AST Projection ─────────────────────────


def _ollama_list_vision_models():
    base = _ollama_base_url()
    try:
        req = urlrequest.Request(f"{base}/api/tags", method="GET")
        with urlrequest.urlopen(req, timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return []
    out = []
    for item in payload.get("models") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        lower = name.lower()
        caps = item.get("capabilities") or []
        if any(k in lower for k in ("llava", "bakllava", "vision", "qwen2-vl", "moondream")):
            out.append(name)
        elif "vision" in caps or "image" in caps:
            out.append(name)
    return out


def _resolve_vision_model():
    preferred = os.environ.get("CNEXUS_VISION_MODEL", _CNEXUS_VISION_MODEL).strip() or "llava"
    installed = _ollama_list_vision_models()
    if not installed:
        return preferred
    for name in installed:
        if name == preferred or name.startswith(preferred + ":"):
            return name
    for name in installed:
        if preferred.split(":")[0] in name:
            return name
    return installed[0]


def _parse_visual_relationships(raw_text):
    nodes = {}
    links = []
    for line in str(raw_text or "").splitlines():
        line = line.strip()
        if "->" not in line:
            continue
        parts = re.split(r"\s*->\s*", line, maxsplit=1)
        if len(parts) != 2:
            continue
        a, b = parts[0].strip(" -•*\t"), parts[1].strip(" -•*\t")
        if not a or not b:
            continue
        aid = f"vision:{a}"[:120]
        bid = f"vision:{b}"[:120]
        nodes[aid] = {"id": aid, "label": a[:120], "type": "vision_component", "title": a[:120]}
        nodes[bid] = {"id": bid, "label": b[:120], "type": "vision_component", "title": b[:120]}
        links.append({"source": aid, "target": bid, "type": "vision_flow"})
    return list(nodes.values()), links


def _analyze_architecture_image(image_base64):
    """Ollama vision model → structured component graph."""
    raw = str(image_base64 or "").strip()
    if not raw:
        return [], []
    if "," in raw:
        raw = raw.split(",", 1)[1]
    if not _probe_ollama():
        return [], []
    model = _resolve_vision_model()
    url = f"{_ollama_base_url()}/api/generate"
    prompt = (
        "Identify key system components, blocks, or modules in this architecture diagram.\n"
        "Output ONLY a list of components and their connections in this format:\n"
        "ComponentA -> ComponentB\n"
        "ComponentC -> ComponentA"
    )
    body = {
        "model": model,
        "prompt": prompt,
        "images": [raw],
        "stream": False,
    }
    try:
        req = urlrequest.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=30.0) as response:
            res_data = json.loads(response.read().decode("utf-8", errors="replace"))
            raw_text = res_data.get("response", "")
            return _parse_visual_relationships(raw_text)
    except Exception as exc:
        _append_runtime_log(f"视觉摄入失败 · {exc}", category="capture", level="warn")
        return [], []


def _assets_dir():
    return os.environ.get("CNEXUS_ASSETS_DIR", os.path.join(_PERSIST_DIR, "assets"))


def _describe_image_asset(binary: bytes, filename: str) -> str:
    """Vision-backed description for asset metadata (falls back to size label)."""
    try:
        b64 = base64.b64encode(binary).decode("ascii")
        nodes, _links = _analyze_architecture_image(b64)
        if nodes:
            labels = [str(n.get("label") or n.get("title") or "") for n in nodes[:10]]
            labels = [label for label in labels if label]
            if labels:
                return f"Vision components: {', '.join(labels)}"[:320]
    except Exception:
        pass
    return f"Image asset {filename} ({len(binary)} bytes)"


def _get_asset_processor():
    global _asset_processor
    if _asset_processor is not None:
        return _asset_processor
    try:
        asset_mod = _load_core_module("asset_processor", "asset_processor.py")
        _asset_processor = asset_mod.AssetProcessor(
            _assets_dir(),
            audit_log=_get_audit_log(),
            audit_fn=_audit_event,
            vision_fn=_describe_image_asset,
        )
    except Exception:
        _asset_processor = None
    return _asset_processor


def _asset_vector_index_path():
    return os.environ.get("CNEXUS_ASSET_VECTOR_INDEX", os.path.join(_assets_dir(), "vector_index.json"))


def _asset_push_queue_path():
    return os.environ.get("CNEXUS_ASSET_PUSH_QUEUE", os.path.join(_PERSIST_DIR, "asset_push_queue.json"))


def _clip_enabled():
    return os.environ.get("CNEXUS_CLIP_ENABLE", "1").lower() not in ("0", "false", "no")


def _get_clip_embedder():
    global _clip_embedder
    if _clip_embedder is not None:
        return _clip_embedder
    if not _clip_enabled():
        _clip_embedder = False
        return None
    try:
        clip_mod = _load_core_module("clip_embed", "clip_embed.py")
        _clip_embedder = clip_mod.ClipEmbedder(enabled=True)
    except Exception:
        _clip_embedder = False
    return _clip_embedder if _clip_embedder is not False else None


def _asset_embed_enabled():
    return os.environ.get("CNEXUS_ASSET_EMBED_ENABLE", "1").lower() not in ("0", "false", "no")


def _asset_peer_push_enabled():
    return os.environ.get("CNEXUS_ASSET_PEER_PUSH", "1").lower() in ("1", "true", "yes")


def _asset_peer_pull_enabled():
    return os.environ.get("CNEXUS_ASSET_PEER_PULL", "1").lower() not in ("0", "false", "no")


def _asset_push_max_bytes():
    try:
        return int(os.environ.get("CNEXUS_ASSET_PUSH_MAX_BYTES", "5242880"))
    except ValueError:
        return 5242880


def _asset_signed_headers(payload: dict):
    im = _get_identity_manager()
    mw = _get_auth_middleware()
    if im is None or mw is None:
        return {}
    return mw.build_signed_headers(im, payload)


def _get_asset_vector_index():
    global _asset_vector_index
    if _asset_vector_index is not None:
        return _asset_vector_index
    try:
        idx_mod = _load_core_module("asset_vector_index", "asset_vector_index.py")
        proc = _get_asset_processor()
        embed_fn = _get_embedding_with_fallback if _asset_embed_enabled() else None
        clip_embedder = _get_clip_embedder()

        def _read_blob(asset_id: str, meta: dict):
            if proc is None:
                return None
            blob, _, _ = proc.read_raw(asset_id)
            return blob

        _asset_vector_index = idx_mod.AssetVectorIndex(
            _asset_vector_index_path(),
            embed_fn=embed_fn,
            clip_embedder=clip_embedder,
            read_blob_fn=_read_blob if proc else None,
            enabled=_asset_embed_enabled(),
        )
    except Exception:
        _asset_vector_index = None
    return _asset_vector_index


def _get_asset_peer_sync():
    global _asset_peer_sync
    if _asset_peer_sync is not None:
        return _asset_peer_sync
    proc = _get_asset_processor()
    if proc is None:
        return None
    try:
        sync_mod = _load_network_module("asset_peer_sync", "asset_peer_sync.py")
        _asset_peer_sync = sync_mod.AssetPeerSync(
            proc,
            _get_peer_registry(),
            build_signed_headers=_asset_signed_headers,
            max_push_bytes=_asset_push_max_bytes(),
        )
    except Exception:
        _asset_peer_sync = None
    return _asset_peer_sync


def _get_asset_push_queue():
    global _asset_push_queue
    if _asset_push_queue is not None:
        return _asset_push_queue
    if not _asset_peer_push_enabled():
        return None
    sync = _get_asset_peer_sync()
    if sync is None:
        return None
    try:
        queue_mod = _load_network_module("asset_push_queue", "asset_push_queue.py")
        _asset_push_queue = queue_mod.AssetPushRetryQueue(
            _asset_push_queue_path(),
            sync,
        )
        sync.push_queue = _asset_push_queue
        _asset_push_queue.start_worker()
    except Exception:
        _asset_push_queue = None
    return _asset_push_queue


def _start_asset_push_retry():
    if _asset_peer_push_enabled():
        _get_asset_push_queue()


def _after_asset_indexed(result: dict):
    if not result.get("ok"):
        return
    asset_id = str(result.get("id") or "")
    meta = dict(result.get("meta") or {})
    proc = _get_asset_processor()
    if proc and asset_id and not meta:
        reader = getattr(proc, "_read_meta", None)
        if callable(reader):
            meta = dict(reader(asset_id) or {})

    idx = _get_asset_vector_index()
    if idx and asset_id and meta:
        image_bytes = None
        if meta.get("type") == "image" and proc:
            blob, _, _ = proc.read_raw(asset_id)
            image_bytes = blob
        idx.index_asset(asset_id, meta, image_bytes=image_bytes)

    if _asset_peer_push_enabled() and asset_id and result.get("status") == "indexed":
        sync = _get_asset_peer_sync()
        if sync:
            sync.push_asset_async(asset_id)


def _asset_blob_present(asset_id: str) -> bool:
    proc = _get_asset_processor()
    if proc is None:
        return False
    blob, _, status = proc.read_raw(str(asset_id or "").strip())
    return blob is not None and status == 200


def _upgrade_memory_blocks_for_asset(asset_id: str):
    proc = _get_asset_processor()
    prov = _get_provenance()
    if proc is None:
        return
    asset_id = str(asset_id or "").strip()
    blob, meta, status = proc.read_raw(asset_id)
    if blob is None or status != 200:
        return
    kind = (meta or {}).get("type") or "code"
    if kind == "code":
        content = blob.decode("utf-8", errors="replace")
    else:
        content = str((meta or {}).get("desc") or (meta or {}).get("summary") or (meta or {}).get("filename") or asset_id)
    for block in _engine_state["memory_store"].blocks:
        data = dict(block.get("data") or {})
        if str(data.get("asset_id") or "") != asset_id:
            continue
        if prov:
            data = prov.block_data_with_provenance(
                data,
                provenance=prov.PROVENANCE_LOCAL_FULL,
                source_peer=str(data.get("source_peer") or (meta or {}).get("source_peer") or ""),
            )
        else:
            data["provenance"] = "local-full"
            data["content_kind"] = "full"
        data["content"] = content[:2000]
        data["replayed"] = False
        block["data"] = data


def _ensure_asset_local(asset_id: str, *, source_peer: str = "", peer_host: str = "", auto_pull: bool | None = None) -> dict:
    asset_id = str(asset_id or "").strip()
    if _asset_blob_present(asset_id):
        return {"ok": True, "asset_id": asset_id, "local": True, "status": "already_present"}
    if auto_pull is None:
        auto_pull = _asset_peer_pull_enabled()
    if not auto_pull:
        return {"ok": False, "asset_id": asset_id, "local": False, "error": "blob_missing"}

    proc = _get_asset_processor()
    reg = _get_peer_registry()
    im = _get_identity_manager()
    mw = _get_auth_middleware()
    build_headers = mw.build_signed_headers if mw and im else None
    try:
        pull_mod = _load_network_module("asset_peer_pull", "asset_peer_pull.py")
        report = pull_mod.pull_asset_into_local(
            asset_id,
            proc,
            reg,
            source_peer=source_peer,
            peer_host=peer_host,
            identity_manager=im,
            build_signed_headers=build_headers,
            try_trusted_fallback=not bool(source_peer or peer_host),
        )
    except Exception as exc:
        return {"ok": False, "asset_id": asset_id, "local": False, "error": str(exc)}

    if report.get("ok"):
        _after_asset_indexed({"ok": True, "id": asset_id, "status": report.get("status"), "meta": report.get("meta")})
        _upgrade_memory_blocks_for_asset(asset_id)
        _schedule_persist()
    return report


def _load_federated_search_module():
    try:
        return _load_network_module("asset_federated_search", "asset_federated_search.py")
    except Exception:
        return None


def _assets_status():
    return _assets_status_service.build()


def _model_public(row):
    return ModelConfigService.to_public(row)


def _active_chat_model_id():
    return _model_service.active_model_id()


def _upsert_model(model_id, body, create=False):
    return _model_service.upsert(model_id, body, create=create)


def _ollama_base_url():
    return _model_service.ollama_base_url()


def _ollama_list_chat_models(base_url=None):
    return _model_service.list_ollama_chat_models(base_url)


def _resolve_ollama_model_name(preferred, installed):
    return ModelConfigService.resolve_ollama_model_name(preferred, installed)


def _sync_ollama_registry(force=False):
    _model_service.sync_ollama_registry(force=force)
    return _shadow_projection_service.ollama_status()


def _probe_ollama():
    try:
        req = urlrequest.Request(f"{_ollama_base_url()}/api/tags", method="GET")
        with urlrequest.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _find_ollama_binary():
    found = shutil.which("ollama")
    if found:
        return found
    for candidate in (
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
    ):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


# ── Shadow API projections (personal L0 → enterprise contract shapes) ─────


def _speech_text(speech):
    return speech_text(speech)


def _decision_intent(decision):
    return decision_intent(decision)


def _estimate_tokens(text):
    if not text:
        return 0
    return max(1, int(len(str(text)) * 0.75))


def _cost_level(total):
    if total < 400:
        return "low"
    if total < 1500:
        return "mid"
    if total < 4000:
        return "high"
    return "spike"


def _record_token_trace(
    trace_id,
    input_text,
    output_text,
    entry="converse",
    mode="fast",
    tokens_in=None,
    tokens_out=None,
    source="estimated",
    model_id=None,
    provider=None,
):
    tin = tokens_in if tokens_in is not None else _estimate_tokens(input_text)
    tout = tokens_out if tokens_out is not None else _estimate_tokens(output_text)
    total = tin + tout
    row = {
        "trace_id": trace_id,
        "tokens_in": tin,
        "tokens_out": tout,
        "total": total,
        "mode": mode,
        "cost_level": _cost_level(total),
        "entry": entry,
        "event_count": 7,
        "source": source,
        "model_id": model_id,
        "provider": provider,
    }
    _engine_state.setdefault("token_traces", []).append(row)
    if len(_engine_state["token_traces"]) > 10:
        _engine_state["token_traces"] = _engine_state["token_traces"][-10:]


def _header_lookup_peer(headers):
    for key in ("X-CNexus-Pubkey", "x-cnexus-pubkey"):
        val = headers.get(key) if hasattr(headers, "get") else None
        if val:
            return val
    return ""


def _init_status_gateway():
    global _status_subsystems_service, _network_status_service, _identity_status_service
    global _audit_chain_status_service, _api_auth_status_service, _consensus_status_service
    global _assets_status_service, _resilience_status_service, _peers_status_service
    global _status_snapshot_service, _dashboard_status_service, _shadow_projection_service

    bundle = build_status_services(
        _state_manager,
        _activation_service,
        StatusBootstrapHooks(
            consolidation=ConsolidationStatusHooks(
                rem_consolidation_status=_memory_rem_service.consolidation_status,
                build_rem_context=_memory_rem_service.build_context,
            ),
            replay=ReplayStatusHooks(
                get_log_replay_engine=_get_log_replay_engine,
                get_audit_log=_get_audit_log,
                get_state_reconstructor=_get_state_reconstructor,
            ),
            awakening=AwakeningStatusHooks(
                read_awakening_base=_read_awakening_base,
                genesis_status=_genesis_status,
                reconstructor_status=_reconstructor_status,
            ),
            pruning=PruningStatusHooks(get_cognitive_pruning_engine=_get_cognitive_pruning_engine),
            entropy=EntropyStatusHooks(
                get_entropy_store=_get_entropy_store,
                get_peer_registry=_get_peer_registry,
            ),
            persistence=PersistenceStatusHooks(
                persist_version=_PERSIST_VERSION,
                persist_file_path=_persist_file_path,
                persist_meta=lambda: _persist_meta,
            ),
            negotiation_conflict=NegotiationConflictStatusHooks(
                negotiation_conflict_enabled=_negotiation_conflict_enabled,
                negotiation_conflict_use_llm=_negotiation_conflict_use_llm,
                negotiation_conflict_context=_negotiation_conflict_context,
            ),
            reflection=ReflectionStatusHooks(reflection_engine_status=_reflection_engine_status),
            conflict_resolution=ConflictResolutionStatusHooks(
                conflict_agent_status=_conflict_agent_status,
                negotiation_conflict_enabled=_negotiation_conflict_enabled,
                negotiation_conflict_use_llm=_negotiation_conflict_use_llm,
            ),
            network=NetworkStatusHooks(
                get_connectivity_manager=_get_connectivity_manager,
                get_dht_service=_get_dht_service,
                get_network_firewall=_get_network_firewall,
            ),
            identity=IdentityStatusHooks(
                identity_optional=_identity_optional,
                identity_key_path=_identity_key_path,
                get_identity_manager=_get_identity_manager,
            ),
            audit_chain=AuditChainStatusHooks(
                audit_optional=_audit_optional,
                audit_log_path=_audit_log_path,
                get_audit_log=_get_audit_log,
                get_audit_integrity=lambda: _audit_integrity,
            ),
            api_auth=ApiAuthStatusHooks(get_auth_middleware=_get_auth_middleware),
            consensus=ConsensusStatusHooks(
                get_negotiation_manager=_get_negotiation_manager,
                get_reputation_registry=_get_reputation_registry,
            ),
            assets=AssetsStatusHooks(
                asset_embed_enabled=_asset_embed_enabled,
                clip_enabled=_clip_enabled,
                asset_peer_push_enabled=_asset_peer_push_enabled,
                asset_peer_pull_enabled=_asset_peer_pull_enabled,
                get_asset_vector_index=_get_asset_vector_index,
                get_asset_peer_sync=_get_asset_peer_sync,
                get_asset_push_queue=_get_asset_push_queue,
                get_asset_processor=_get_asset_processor,
            ),
            resilience=ResilienceStatusHooks(
                get_metrics_module=_get_metrics_module,
                get_gossip_sync=_get_gossip_sync,
                get_peer_registry=_get_peer_registry,
                heartbeat_stale_seconds=_heartbeat_stale_seconds,
            ),
            peers=PeersStatusHooks(
                peer_registry_path=_peer_registry_path,
                get_peer_registry=_get_peer_registry,
                get_gossip_sync=_get_gossip_sync,
            ),
            dashboard=DashboardStatusHooks(
                get_metrics_module=_get_metrics_module,
                get_audit_log=_get_audit_log,
                get_gossip_sync=_get_gossip_sync,
                get_peer_registry=_get_peer_registry,
                heartbeat_stale_seconds=_heartbeat_stale_seconds,
                server_port=_SERVER_PORT,
            ),
            shadow=ShadowProjectionHooks(
                find_ollama_binary=_find_ollama_binary,
                probe_ollama=_probe_ollama,
                ollama_host=OLLAMA_HOST,
                active_chat_model_id=_active_chat_model_id,
            ),
        ),
    )

    _status_subsystems_service = bundle.subsystems
    _network_status_service = bundle.network
    _identity_status_service = bundle.identity
    _audit_chain_status_service = bundle.audit_chain
    _api_auth_status_service = bundle.api_auth
    _consensus_status_service = bundle.consensus
    _assets_status_service = bundle.assets
    _resilience_status_service = bundle.resilience
    _peers_status_service = bundle.peers
    _status_snapshot_service = bundle.snapshot
    _dashboard_status_service = bundle.dashboard
    _shadow_projection_service = bundle.shadow


def _init_project_control_gateway():
    global _project_control_service
    _project_control_service = ProjectControlService(
        ProjectControlHooks(
            mutate_engine=_state_manager.mutate,
            schedule_persist=_schedule_persist,
            audit_event=_audit_event,
        )
    )
    _project_control_service.ensure_default()


def _scratch_status():
    from gateway.services.conversation_scratch import normalize_scratch, prune_scratch, scratch_status

    return _state_manager.mutate(lambda engine: scratch_status(prune_scratch(normalize_scratch(engine))))


def _clear_conversation_scratch():
    from gateway.services.conversation_scratch import clear_scratch

    result = clear_scratch(_state_manager.mutate)
    _schedule_persist()
    return result


def _init_status_routes_gateway():
    global _system_probe_service, _status_routes
    _system_probe_service = SystemProbeService(_state_manager)
    _status_routes = SystemStatusRouteHandler(
        _system_probe_service,
        _status_subsystems_service,
        _status_snapshot_service,
        _dashboard_status_service,
        _peers_status_service,
        _network_status_service,
        _shadow_projection_service,
        _memory_recall_service,
        _gateway_intent_service,
        project_control=_project_control_service,
        scratch_status_fn=_scratch_status,
    )


def _init_control_gateway():
    global _conflict_control_service, _pruning_control_service, _consensus_control_service
    global _memory_control_service, _replay_control_service, _reflection_control_service
    global _rem_control_service, _control_plane_service

    bundle = build_control_services(
        _shadow_projection_service,
        ControlBootstrapHooks(
            conflict=ConflictControlHooks(
                get_conflict_agent=_get_conflict_agent,
                run_conflict_resolution=_run_conflict_resolution,
                conflict_resolution_status=_conflict_resolution_status,
                set_negotiation_conflict_llm=_set_negotiation_conflict_llm,
                set_negotiation_conflict_enabled=_set_negotiation_conflict_enabled,
            ),
            pruning=PruningControlHooks(get_pruning_engine=_get_cognitive_pruning_engine),
            consensus=ConsensusControlHooks(
                get_reputation_registry=_get_reputation_registry,
                get_network_firewall=_get_network_firewall,
                audit_event=_audit_event,
            ),
            memory=MemoryControlHooks(
                audit_event=_audit_event,
                get_current_model_registry=lambda: dict(_engine_state.get("model_registry", {})),
                default_model_registry=_default_model_registry,
                reset_engine_memory=_reset_engine_memory,
                persist_file_path=_persist_file_path,
                append_runtime_log=_append_runtime_log,
                persist_engine_state=_persist_engine_state,
                persistence_status=_persistence_status,
                cancel_scheduled_persist=_cancel_scheduled_persist,
                persist_engine_state_fast=_persist_engine_state_fast,
                mutate_memory_store=_state_manager.mutate_memory_store,
                schedule_persist=_schedule_persist,
                constitution_dir=lambda: os.path.join(_BASE_DIR, "runtime", "constitution"),
                foundation_dir=lambda: os.path.join(_BASE_DIR, "runtime", "foundation"),
                recompile_runtime=lambda force=False: _recompile_runtime(force=force),
                get_runtime_status=lambda: dict((_engine_state.get("runtime") or {}).get("status") or {}),
            ),
            replay=ReplayControlHooks(run_log_replay=_run_log_replay),
            reflection=ReflectionControlHooks(run_self_reflection=_run_self_reflection),
            rem=RemControlHooks(run_rem_deep_sleep=_memory_rem_service.run_deep_sleep),
        ),
    )

    _conflict_control_service = bundle.conflict
    _pruning_control_service = bundle.pruning
    _consensus_control_service = bundle.consensus
    _memory_control_service = bundle.memory
    _replay_control_service = bundle.replay
    _reflection_control_service = bundle.reflection
    _rem_control_service = bundle.rem
    _control_plane_service = bundle.control_plane


def _init_auth_gateway():
    global _auth_gate
    _auth_gate = AuthGate(_cnexus_auth_deny)


def _init_projection_register_gateway():
    global _projection_register_service
    _projection_register_service = ProjectionRegisterService(
        _state_manager,
        ProjectionRegisterHooks(
            schedule_projection_wormhole=_schedule_projection_wormhole,
            append_runtime_log=_append_runtime_log,
            schedule_persist=_schedule_persist,
        ),
        activation_max_score=_ACTIVATION_MAX_SCORE,
    )


def _init_projection_ingest_gateway():
    global _projection_ingest_service
    _projection_ingest_service = ProjectionIngestService(
        ProjectionIngestHooks(analyze_architecture_image=_analyze_architecture_image),
        _projection_register_service,
    )


def _init_asset_route_gateway():
    global _memory_asset_service, _asset_gateway_service, _peer_mesh_service
    global _asset_routes, _peer_routes

    bundle = build_asset_route_services(
        _state_manager,
        _memory_recall_service,
        _auth_gate,
        _ingest_routes,
        _projection_ingest_service,
        AssetRouteBootstrapHooks(
            memory_asset=MemoryAssetHooks(
                load_federated_search_module=_load_federated_search_module,
                get_peer_registry=_get_peer_registry,
                get_dht_service=_get_dht_service,
                get_identity_manager=_get_identity_manager,
                build_signed_headers=_asset_signed_headers,
                blob_present=_asset_blob_present,
                peer_pull_enabled=_asset_peer_pull_enabled,
                ensure_local=_ensure_asset_local,
                get_asset_processor=_get_asset_processor,
            ),
            asset_gateway=AssetGatewayHooks(
                get_asset_processor=_get_asset_processor,
                get_vector_index=_get_asset_vector_index,
                get_clip_embedder=_get_clip_embedder,
                get_asset_peer_sync=_get_asset_peer_sync,
                get_asset_push_queue=_get_asset_push_queue,
                after_asset_indexed=_after_asset_indexed,
                schedule_persist=_schedule_persist,
                asset_peer_push_enabled=_asset_peer_push_enabled,
            ),
            peer_mesh=PeerMeshHooks(
                get_audit_log=_get_audit_log,
                get_peer_registry=_get_peer_registry,
                get_gossip_sync=_get_gossip_sync,
                get_genesis_sync=_get_genesis_sync,
                get_p2p_handler=_get_p2p_handler,
                get_negotiation_manager=_get_negotiation_manager,
                get_entropy_store=_get_entropy_store,
                get_connectivity_manager=_get_connectivity_manager,
                get_dht_service=_get_dht_service,
                get_network_firewall=_get_network_firewall,
                header_lookup_peer=_header_lookup_peer,
                verify_audit_integrity=_verify_audit_integrity,
                identity_pubkey=lambda: (_identity_status().get("pubkey") or ""),
                audit_event=_audit_event,
                perform_outbound_handshake=_perform_outbound_handshake,
                local_peer_host=_local_peer_host,
                get_catalog_service=_get_catalog_service,
                get_cognitive_service=_get_cognitive_service,
                get_storage_service=_get_storage_service,
                get_repair_service=_get_repair_service,
                get_application_service=_get_application_service,
                memory_block_count=lambda: len(_engine_state["memory_store"].blocks),
                trace_count=lambda: len(_engine_state.get("trace", [])),
            ),
        ),
        touch_activity=_state_manager.touch_consolidation_activity,
    )

    _memory_asset_service = bundle.memory_asset
    _asset_gateway_service = bundle.asset_gateway
    _peer_mesh_service = bundle.peer_mesh
    _asset_routes = bundle.asset_routes
    _peer_routes = bundle.peer_routes


def _init_control_routes_gateway():
    global _control_routes
    _control_routes = ControlRouteHandler(
        _control_plane_service,
        _status_snapshot_service,
        _gateway_intent_service,
        project_control=_project_control_service,
        clear_scratch=_clear_conversation_scratch,
    )


def _init_static_routes_gateway():
    global _static_routes
    ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
    _static_routes = StaticRouteHandler(ui_dir)


def _init_gateway_intent_gateway():
    global _gateway_intent_service
    _gateway_intent_service = GatewayIntentService(_converse_service, _ingest_service)


def _load_gateway_file(subfile: str, fullname: str, package: str):
    import importlib.util as u

    if fullname in sys.modules:
        return sys.modules[fullname]
    path = os.path.join(GATEWAY_DIR, subfile)
    spec = u.spec_from_file_location(fullname, path)
    mod = u.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[fullname] = mod
    spec.loader.exec_module(mod)
    return mod


def _init_expert_gateway():
    global _expert_routes
    pkg = "cnexus_gateway"
    gw_mod = _load_gateway_file(
        os.path.join("services", "expert_gateway.py"),
        f"{pkg}.services.expert_gateway",
        f"{pkg}.services",
    )
    rt_mod = _load_gateway_file(
        os.path.join("routes", "expert.py"),
        f"{pkg}.routes.expert",
        f"{pkg}.routes",
    )
    service = gw_mod.ExpertGatewayService(
        _state_manager,
        schedule_persist=_schedule_persist,
        resolve_model=lambda: _model_service.resolve_model_row_for_chat(None),
        llm_invoke=_llm_service.invoke,
    )
    _expert_routes = rt_mod.ExpertRouteHandler(service)


def _init_v2_handler():
    global V2Handler
    V2Handler = create_v2_handler(
        V2Bindings(
            models_routes=_models_routes,
            converse_routes=_converse_routes,
            ingest_routes=_ingest_routes,
            status_routes=_status_routes,
            asset_routes=_asset_routes,
            peer_routes=_peer_routes,
            control_routes=_control_routes,
            static_routes=_static_routes,
            auth_gate=_auth_gate,
            put_routes=build_put_routes(_models_routes),
            post_routes=build_post_routes(
                _converse_routes,
                _asset_routes,
                _peer_routes,
                _ingest_routes,
                _control_routes,
                _models_routes,
                expert=_expert_routes,
            ),
            expert_routes=_expert_routes,
        )
    )


_init_memory_graph_gateway()
_init_memory_rem_gateway()
_init_activation_gateway()
_init_memory_recall_gateway()
_init_negotiation_gateway()
_init_audit_emitter_gateway()
_init_converse_audit_gateway()
_init_turn_persistence_gateway()
_init_project_control_gateway()
_init_converse_gateway()
_init_gateway_intent_gateway()
_init_status_gateway()
_init_status_routes_gateway()
_init_auth_gateway()
_init_control_gateway()
_init_projection_register_gateway()
_init_projection_ingest_gateway()
_init_asset_route_gateway()
_init_control_routes_gateway()
_init_static_routes_gateway()
_init_expert_gateway()
_init_v2_handler()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    global _SERVER_PORT
    try:
        _SERVER_PORT = int(os.environ.get("CNEXUS_PORT", "7864"))
    except ValueError:
        _SERVER_PORT = 7864
    port = _SERVER_PORT
    loaded = _load_engine_state_on_boot()
    persist_path = _persist_file_path()
    _install_signed_memory_store(_engine_state["memory_store"])
    try:
        boot = _boot_cnexus_runtime()
        if boot.get("ok"):
            _append_runtime_log(
                f"Runtime BOOT · phase={boot.get('boot_phase')} "
                f"constitution={boot.get('constitution_docs', 0)} policy={boot.get('policy_docs', 0)}",
                category="control_plane",
            )
    except Exception as exc:
        _append_runtime_log(f"Runtime BOOT 失败 · {exc}", category="control_plane", level="warn")
    try:
        migrated = _memory_control_service.migrate_protected_labels()
        if migrated.get("migrated") or migrated.get("archived_runtime"):
            _append_runtime_log(
                f"Memory 迁移 · foundation标签={migrated.get('migrated', 0)} "
                f"归档Runtime残留={migrated.get('archived_runtime', 0)}",
                category="control_plane",
            )
    except Exception as exc:
        _append_runtime_log(f"Foundation 迁移失败 · {exc}", category="control_plane", level="warn")
    try:
        foundation_boot = _memory_control_service.bootstrap_foundation()
        if foundation_boot.get("loaded") or foundation_boot.get("upgraded"):
            _schedule_persist()
    except Exception as exc:
        _append_runtime_log(f"Foundation BOOT 失败 · {exc}", category="control_plane", level="warn")
    try:
        share_boot = _bootstrap_share_local_memory()
        if share_boot.get("shared"):
            _append_runtime_log(
                f"本地记忆已发布 · graph={share_boot.get('graph_id', '')[:16]}… "
                f"blocks={share_boot.get('block_count', 0)}",
                category="control_plane",
            )
        elif share_boot.get("skipped") and share_boot.get("reason") not in ("disabled", "no_blocks", "application_unavailable"):
            pass
        elif share_boot.get("error"):
            _append_runtime_log(f"本地记忆分享失败 · {share_boot.get('error')}", category="control_plane", level="warn")
    except Exception as exc:
        _append_runtime_log(f"本地记忆分享启动失败 · {exc}", category="control_plane", level="warn")
    _maybe_replay_on_boot()
    identity = _identity_status()
    audit_state = _verify_audit_integrity()
    if audit_state.get("ok") is False:
        _append_runtime_log(
            f"审计链完整性失败 · {audit_state.get('message')}",
            category="control_plane",
            level="error",
        )
    server = ThreadingHTTPServer((_bind_host(), port), V2Handler)
    server.allow_reuse_address = True
    bind = _bind_host()
    print(f" CNexus 2.0 Unified Server live on http://{bind if bind != '0.0.0.0' else '127.0.0.1'}:{port} (bind={bind})")
    print(f"   GET  /              — Next.js static frontend (6 views)")
    print(f"   GET  /api/status    — L0 cognitive state snapshot")
    print(f"   GET  /api/dashboard/status — Mission Control metrics")
    print(f"   GET  /mission-control — Network observability dashboard")
    rem = _get_rem_engine()
    if rem and rem.enabled:
        print(f"   REM sleep engine: threshold={rem.threshold} · watchdog={rem.watchdog_interval}s")
    print(f"   GET  /api/converse?text=... — run 6-step cycle")
    print(f'   POST /api/converse  -- json: text, converse_mode, thinking_mode (precision|emergent)')
    print(f'   POST /api/converse/stream  -- SSE token stream (text/event-stream)')
    print(f"   POST /v1/memory/rem-sleep — REM deep sleep consolidation")
    print(f"   GET  /v1/runtime/boot — Runtime BOOT status (Constitution + Policy)")
    print(f"   GET  /v1/project/active · POST /v1/project/active — L3 project lock")
    print(f"   GET  /v1/conversation/scratch — L1 session scratch status")
    print(f"   POST /v1/runtime/recompile — recompile constitution.bin from runtime/")
    print(f"   POST /api/ingest/image  — vision architecture projection")
    print(f"   POST /api/ingest/code   — AST code space projection")
    print(f"   POST /api/ingest/document — personal one-shot document upload + index")
    print(f"   POST /api/ingest/documents — batch document upload (fast path)")
    print(f"   POST /api/upload/code   — cognitive asset index (code)")
    print(f"   POST /api/upload/image  — cognitive asset index (image)")
    print(f"   GET  /api/asset/<id>    — asset metadata (lazy fetch for peers)")
    print(f"   GET  /api/asset/search?q= — search assets via AuditLog summaries")
    print(f"   GET  /api/asset/search/semantic?q= — vector similarity search")
    print(f"   POST /api/asset/search/semantic — text or image_base64 semantic search")
    print(f"   GET  /api/asset/push/queue — failed push retry queue status")
    print(f"   POST /api/asset/push — push asset blob to trusted peers")
    print(f"   POST /api/asset/pull — pull asset blob from trusted peer on cache miss")
    print(f"   POST /api/asset/receive — peer ingest endpoint (signed)")
    print(f"   Env  CNEXUS_ASSET_PEER_PULL=1 — auto-pull on recall / semantic search miss")
    print(f"   Env  CNEXUS_ASSET_PEER_PUSH=1 (default) — auto-push indexed assets to trusted peers")
    print(f"   Env  CNEXUS_SHARE_LOCAL_MEMORY=1 (default) — publish local memory to catalog on boot")
    print(f"   Env  CNEXUS_ASSET_EMBED_ENABLE=1 — Ollama/cloud vector index")
    print(f"   Genesis handshake: CNEXUS_GENESIS_ENABLE=1 — full AuditLog mirror on boot")
    print(f"   Resilience score: GET /api/status → resilience.score")
    print(f"   POST /api/connectivity/connect — DHT + ICE path selection to peer")
    print(f"   POST /api/dht/rpc — Kademlia FIND_NODE / STORE")
    print(f"   POST /api/network/firewall/ban — evict malicious peer from routing")
    print(f"   Env  CNEXUS_BIND_HOST=0.0.0.0 CNEXUS_PUBLIC_URL= CNEXUS_DHT_BOOTSTRAP=")
    print(f"   POST /api/reflect/meta — metacognitive reflection over AuditLog")
    print(f"   POST /api/conflict/resolve — adversarial memory conflict merge/fork")
    print(f"   GET  /api/entropy/status — local + mesh consensus entropy (Genesis XOR)")
    print(f"   Env  CNEXUS_ENTROPY_SYNC=1 — exchange entropy_seed on Genesis handshake")
    print(f"   GET  /api/conflict/negotiation — recent auto-resolved negotiation conflicts")
    print(f"   POST /api/conflict/settings — runtime toggle for negotiation LLM auto-resolve")
    print(f"   GET  /api/pruning/status · POST /api/pruning/run — cognitive pruning cycle")
    print(f"   Env  CNEXUS_COGNITIVE_PRUNING=1 — frequency forgetting + dispute summarization")
    print(f"   Env  CNEXUS_NEGOTIATION_CONFLICT=1 — auto ConflictAgent on negotiation failure")
    print(f"   Env  CNEXUS_NEGOTIATION_CONFLICT_LLM=1 — use LLM for auto negotiation conflicts")
    print(f"   Env  CNEXUS_REFLECT_LIMIT=100 CNEXUS_REFLECT_WINDOW_DAYS=7")
    print(f"   Log replay: POST /api/replay/run — snapshot + incremental cognitive reconstruction")
    print(f"   Env  CNEXUS_SNAPSHOT_INTERVAL=1000 — cognitive snapshot cadence during replay")
    print(f"   Env  CNEXUS_REPLAY_ON_BOOT=1 — auto-replay when state lags audit")
    print(f"   POST /api/memory/clear  — wipe memory + delete snapshot (keep_models optional)")
    print(f"   JSON persist: {persist_path} ({'restored' if loaded else 'fresh start'})")
    if identity.get("loaded"):
        print(f"   Identity Ed25519: {identity.get('pubkey', '')[:16]}…")
    elif identity.get("enabled"):
        print("   Identity: enabled (install pynacl: pip install pynacl)")
    if audit_state.get("ok") is False:
        print(f"   ⚠ Audit chain integrity FAILED: {audit_state.get('message')}")
    elif audit_state.get("entries", 0):
        print(f"   Audit chain: {audit_state.get('entries')} entries · {audit_state.get('message')}")
    _start_rem_watchdog()
    _start_peer_heartbeat()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        with _persist_lock:
            if _persist_timer is not None:
                _persist_timer.cancel()
        _persist_engine_state()
        server.server_close()

if __name__ == "__main__":
    main()
