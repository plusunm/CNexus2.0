"""Memory Domain — query, context, provenance, graph, asset."""

from .asset import MemoryAssetHooks, MemoryAssetService
from .context import MemoryContextService
from .graph import MemoryGraphConfig, MemoryGraphHooks, MemoryGraphService, default_normalize_memory_tag
from .provenance import (
    CoreModuleProvenanceAdapter,
    DefaultProvenancePort,
    ProvenancePort,
)
from .query import MemoryQueryService, MemoryRecallService
from .rem import MemoryRemConfig, MemoryRemHooks, MemoryRemService
from .rem_synthesis import (
    RemConsolidationSynthesisConfig,
    RemConsolidationSynthesisHooks,
    RemConsolidationSynthesizer,
    heuristic_compact_facts,
    parse_consolidation_facts,
)
from .protection import (
    block_memory_level,
    format_constitution_preamble,
    infer_memory_level_from_ingest,
    is_clear_protected,
    is_prune_protected,
    level_policy,
    level_priority,
    normalize_memory_level,
    stamp_block_protection,
)
from .types import MemoryFragment, MemoryRecallHooks, QueryFilters, RecallResult, TraceEntry
from .wormhole_embed import WormholeEmbedder, WormholeEmbedderHooks

__all__ = [
    "CoreModuleProvenanceAdapter",
    "DefaultProvenancePort",
    "MemoryAssetHooks",
    "MemoryAssetService",
    "MemoryContextService",
    "MemoryGraphConfig",
    "MemoryGraphHooks",
    "MemoryGraphService",
    "MemoryQueryService",
    "MemoryRecallService",
    "MemoryRemConfig",
    "MemoryRemHooks",
    "MemoryRemService",
    "RemConsolidationSynthesisConfig",
    "RemConsolidationSynthesisHooks",
    "RemConsolidationSynthesizer",
    "heuristic_compact_facts",
    "parse_consolidation_facts",
    "MemoryRecallHooks",
    "MemoryFragment",
    "ProvenancePort",
    "RecallResult",
    "QueryFilters",
    "TraceEntry",
    "WormholeEmbedder",
    "WormholeEmbedderHooks",
    "default_normalize_memory_tag",
    "block_memory_level",
    "format_constitution_preamble",
    "infer_memory_level_from_ingest",
    "is_clear_protected",
    "is_prune_protected",
    "level_policy",
    "level_priority",
    "normalize_memory_level",
    "stamp_block_protection",
]
