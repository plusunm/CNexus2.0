"""Backward-compatible shim — Memory Domain lives under services.memory."""

from .memory import MemoryQueryService, MemoryRecallService
from .memory.types import MemoryRecallHooks

__all__ = ["MemoryQueryService", "MemoryRecallService", "MemoryRecallHooks"]
