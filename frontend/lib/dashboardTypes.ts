export type DashboardPeerRow = {
  pubkey: string;
  pubkey_short?: string;
  host?: string;
  status?: string;
  latency_ms?: number | null;
  aligned?: boolean;
  fork_panic?: boolean;
  local_hash?: string;
  remote_hash?: string;
  checked_at?: number;
};

export type DashboardSyncLogRow = {
  peer?: string;
  at?: number;
  aligned?: boolean;
  error?: string;
  message?: string;
  local_hash?: string;
  remote_hash?: string;
  merge?: string;
  negotiation_status?: string;
  negotiation_error?: string;
  merged_count?: number;
  trust_score?: number;
  memory_conflict_count?: number;
  conflict_audit_id?: string;
};

export type DashboardConsensusRecent = {
  ok?: boolean;
  status?: string;
  error?: string;
  message?: string;
  phase?: string;
  peer_host?: string;
  peer_pubkey?: string;
  merged_count?: number;
  trust_score?: number;
  common_ancestor?: string;
  evidence_count?: number;
  checked_at?: number;
  memory_conflict_count?: number;
  conflict_audit_id?: string;
};

export type DashboardConsensusReputation = {
  trust_score?: number;
  blacklisted?: boolean;
  last_event?: string;
  last_reason?: string;
  updated_at?: number;
};

export type DashboardTopology = {
  nodes: Array<{ id: string; name?: string; category?: number; status?: string }>;
  edges: Array<{ source: string; target: string; lineStyle?: { color?: string } }>;
};

export type DashboardStatus = {
  ok: boolean;
  generated_at?: string;
  node?: {
    id?: string;
    pubkey?: string;
    uptime_label?: string;
    pubkey_short?: string;
    resources?: {
      available?: boolean;
      cpu_percent?: number | null;
      memory_percent?: number | null;
      memory_used_mb?: number | null;
      memory_total_mb?: number | null;
    };
    memory_blocks?: number;
    iteration?: number;
  };
  chain?: {
    last_hash_short?: string;
    last_hash?: string;
    entry_count?: number;
    integrity_ok?: boolean;
  };
  peer_summary?: {
    total?: number;
    online?: number;
    aligned?: number;
    fork_panic?: number;
  };
  peers?: DashboardPeerRow[];
  sync_log?: DashboardSyncLogRow[];
  topology?: DashboardTopology;
  rem?: {
    enabled?: boolean;
    running?: boolean;
    rem_due?: boolean;
    last_rem_label?: string;
    threshold?: number;
    idle_seconds?: number;
    total_pruned?: number;
    total_facts?: number;
    semantic_facts?: number;
  };
  identity?: {
    enabled?: boolean;
    loaded?: boolean;
    algorithm?: string;
    pubkey?: string;
    path?: string;
    error?: string;
    hint?: string;
  };
  consensus?: {
    enabled?: boolean;
    mode?: "optimistic" | "conservative" | string;
    min_trust?: number;
    quorum_ratio?: number;
    reputation_peers?: number;
    recent?: Record<string, DashboardConsensusRecent>;
    reputation?: Record<string, DashboardConsensusReputation>;
  };
  resilience?: {
    score?: number;
    full_sync_nodes?: number;
    total_nodes?: number;
    online_nodes?: number;
    aligned_nodes?: number;
    local_integrity_ok?: boolean;
    label?: string;
    genesis_enabled?: boolean;
    last_bootstrap_at?: number;
  };
  replay?: {
    enabled?: boolean;
    needed?: boolean;
    replayable_total?: number;
    last_report?: {
      memory_blocks?: number;
      trace_rows?: number;
      assets_indexed?: number;
      applied?: number;
      mode?: string;
      summary?: string;
    };
    reconstructor?: {
      snapshot_count?: number;
      latest_snapshot?: {
        entry_index?: number;
        last_log_hash?: string;
      };
    };
  };
  awakening?: DashboardAwakening;
  conflict?: {
    enabled?: boolean;
    negotiation_conflict_enabled?: boolean;
    negotiation_conflict_buffer?: number;
    negotiation_conflict_llm?: boolean;
    negotiation_conflict_llm_runtime?: boolean;
    negotiation_conflict_enabled_runtime?: boolean;
  };
  pruning?: {
    enabled?: boolean;
    active_blocks?: number;
    archived_block_ids?: number;
    knowledge_conclusions?: number;
    total_archived?: number;
    total_summarized?: number;
    last_run_at?: number;
    dispute_tracked?: number;
    ref_tracked?: number;
    last_report?: {
      archived_blocks?: number;
      summaries_created?: number;
    };
  };
  entropy?: {
    enabled?: boolean;
    local_seed?: string;
    global_entropy?: string;
    temperature?: number;
    trusted_peer_seeds?: number;
  };
  error?: string;
};

export type DashboardAwakening = {
  phase?: string;
  label?: string;
  progress?: number;
  message?: string;
  summary?: string;
  alive?: boolean;
  started_at?: number;
  completed_at?: number;
  genesis?: {
    enabled?: boolean;
    bootstrap_at?: number;
    full_sync_peers?: number;
    running?: boolean;
  };
};
