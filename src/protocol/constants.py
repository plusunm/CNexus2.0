"""Frozen CNexus distributed cognitive protocol constants (P0 object model)."""

from __future__ import annotations

# Wire protocol version for Device + Session layers (handshake, capability).
CNEXUS_PROTOCOL_VERSION = "3.0"

# Object-model schema versions (per-type evolution; fields append-only on bump).
PEER_OBJECT_VERSION = 1
GRAPH_OBJECT_VERSION = 1
COMMIT_OBJECT_VERSION = 1
CHUNK_OBJECT_VERSION = 1
CHUNK_DESCRIPTOR_OBJECT_VERSION = 1
MANIFEST_OBJECT_VERSION = 1
PUBLISH_TXN_OBJECT_VERSION = 1
MISSING_DIFF_OBJECT_VERSION = 1
REPAIR_PLAN_OBJECT_VERSION = 1
EXECUTION_POLICY_OBJECT_VERSION = 1
CATALOG_ENTRY_OBJECT_VERSION = 3
SESSION_OBJECT_VERSION = 1

# Crypto suites advertised at handshake (Device/Session only).
CRYPTO_SUITE_ED25519 = "ed25519"

# Capability bitmap — Device/Session advertises supported upper-layer features.
CAP_DEVICE_LAN = 1 << 0
CAP_DEVICE_DHT = 1 << 1
CAP_SESSION_ED25519 = 1 << 2
CAP_CATALOG_BLOOM = 1 << 3
CAP_CATALOG_INDEX = 1 << 4
CAP_COGNITIVE_COMMIT = 1 << 5
CAP_COGNITIVE_DIFF = 1 << 6
CAP_STORAGE_CHUNK = 1 << 7
CAP_MERGE_CONSTITUTION = 1 << 8

DEFAULT_PERSONAL_CAPABILITY = (
    CAP_DEVICE_LAN
    | CAP_DEVICE_DHT
    | CAP_SESSION_ED25519
    | CAP_CATALOG_BLOOM
    | CAP_CATALOG_INDEX
    | CAP_COGNITIVE_COMMIT
    | CAP_STORAGE_CHUNK
)

# P4.5 Chunk Consistency Contract — encoding frozen at raw until P5+.
CHUNK_ENCODING_RAW = "raw"
ALLOWED_CHUNK_ENCODINGS = frozenset({CHUNK_ENCODING_RAW})
CHUNK_COMPRESSION_NONE = "none"

# P5 Integrity-driven repair — deterministic, not autonomous.
REPAIR_STRATEGY_PULL_VERIFY_STORE = "pull_verify_store"
REPAIR_POLICY_DETERMINISTIC = "deterministic"

# P5.3 Execution boundary — repair is permitted, not inferred.
EXECUTION_MODE_MANUAL = "manual"
EXECUTION_GATE_ALLOW = "allow"
EXECUTION_GATE_DENY = "deny"
EXECUTION_GATE_REQUIRE_CONFIRM = "require_confirm"
ALLOWED_SOURCE_REASONS = frozenset(
    {
        "connected_peer",
        "trusted_registry_peer",
        "descriptor_provenance",
    }
)

# Handshake iron rule: these keys must NEVER appear in handshake payloads.
# Handshake must not know what "cognition" is.
HANDSHAKE_FORBIDDEN_KEYS = frozenset(
    {
        "memory",
        "audit",
        "graph",
        "graphs",
        "graph_id",
        "graph_hash",
        "graph_ids",
        "graph_hashes",
        "commit",
        "commits",
        "commit_id",
        "chunk",
        "chunks",
        "chunk_hash",
        "snapshot",
        "snapshots",
        "diff",
        "diffs",
        "catalog",
        "catalog_entry",
        "index",
        "entries",
        "root_hash",
        "bloom",
        "bloom_filter",
        "wormhole",
        "projection",
        "block",
        "blocks",
        "genesis",
        "entropy_seed",
    }
)

# Catalog Layer defaults (P2.1 — dynamic Bloom sizing).
CATALOG_BLOOM_TARGET_FPR = 0.01
CATALOG_BLOOM_EXPECTED_ENTRIES = 512
PEER_ID_HEX_LEN = 64
GRAPH_ID_HEX_LEN = 32
COMMIT_ID_HEX_LEN = 64
ROOT_HASH_HEX_LEN = 64
CHUNK_HASH_HEX_LEN = 64
