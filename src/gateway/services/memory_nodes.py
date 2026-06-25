"""Backward-compatible shim — MemoryGraphService owns node spec collection."""

from .memory.graph import (
    MemoryGraphConfig,
    MemoryGraphHooks,
    MemoryGraphService,
    default_normalize_memory_tag,
)

MemoryNodeSpecService = MemoryGraphService
MemoryNodeSpecHooks = MemoryGraphHooks

__all__ = [
    "MemoryGraphConfig",
    "MemoryGraphService",
    "MemoryGraphHooks",
    "MemoryNodeSpecService",
    "MemoryNodeSpecHooks",
    "default_normalize_memory_tag",
]
