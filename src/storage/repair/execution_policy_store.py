"""Persistent ExecutionPolicy store."""

from __future__ import annotations

import json
import threading
from pathlib import Path

try:
    from protocol.models import ExecutionPolicy
except ImportError:
    from cnexus_protocol.models import ExecutionPolicy


class ExecutionPolicyStore:
    def __init__(self, storage_path: str | Path = "data/execution_policy.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._policy = ExecutionPolicy.default()
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                self._policy = ExecutionPolicy.from_dict(data.get("policy") or data)
        except Exception:
            self._policy = ExecutionPolicy.default()

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump({"policy": self._policy.to_dict()}, handle, ensure_ascii=False, indent=2)

    def get(self) -> ExecutionPolicy:
        with self._lock:
            return self._policy

    def set(self, policy: ExecutionPolicy) -> ExecutionPolicy:
        with self._lock:
            self._policy = policy
            self._persist()
        return policy
