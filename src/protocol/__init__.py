"""
CNexus distributed cognitive protocol — P0 object model.

Layer stack (top → bottom):
  Application  — publish / find / sync / merge (no transport knowledge)
  Cognitive    — Commit DAG, Diff, Merge, Constitution verify
  Catalog      — Bloom filter, Graph index exchange
  Session      — auth, encryption negotiation
  Device       — Peer discovery, NAT, secure hello
  Storage      — Chunk store, content addressing (local)
"""

from .application import CognitiveApplication
from .constants import (
    CNEXUS_PROTOCOL_VERSION,
    DEFAULT_PERSONAL_CAPABILITY,
    HANDSHAKE_FORBIDDEN_KEYS,
)
from .handshake_guard import assert_handshake_clean, find_handshake_violations
from .ids import compute_chunk_hash, compute_commit_id, compute_root_hash, graph_id_for_owner_topic, new_graph_id
from .models import (
    CatalogEntry,
    Chunk,
    ChunkDescriptor,
    Commit,
    Graph,
    GraphMetadata,
    HandshakeHello,
    Manifest,
    MissingDiff,
    Peer,
    PublishTxn,
    RepairPlan,
    ExecutionPolicy,
    Session,
)

__all__ = [
    "CNEXUS_PROTOCOL_VERSION",
    "DEFAULT_PERSONAL_CAPABILITY",
    "HANDSHAKE_FORBIDDEN_KEYS",
    "CatalogEntry",
    "Chunk",
    "ChunkDescriptor",
    "CognitiveApplication",
    "Commit",
    "ExecutionPolicy",
    "Graph",
    "GraphMetadata",
    "HandshakeHello",
    "Manifest",
    "MissingDiff",
    "Peer",
    "PublishTxn",
    "RepairPlan",
    "Session",
    "assert_handshake_clean",
    "compute_chunk_hash",
    "compute_commit_id",
    "compute_root_hash",
    "find_handshake_violations",
    "graph_id_for_owner_topic",
    "new_graph_id",
]
