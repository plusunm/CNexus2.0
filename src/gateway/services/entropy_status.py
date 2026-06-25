"""Entropy store status fragment for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class EntropyStatusHooks:
    get_entropy_store: Callable[[], Any]
    get_peer_registry: Callable[[], Any]


class EntropyStatusService:
    def __init__(self, hooks: EntropyStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        store = self._hooks.get_entropy_store()
        if not store:
            return {"enabled": False}
        return store.status(self._hooks.get_peer_registry())
