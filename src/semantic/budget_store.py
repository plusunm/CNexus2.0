"""Atomic persistence for SemanticBudgetState — survives restart without EMA reset."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Optional

from .types import SemanticBudgetState

_PERSIST_VERSION = "scp-budget-v1"
_lock = threading.Lock()


def default_budget_file() -> str:
    base = os.environ.get("CNEXUS_DATA_DIR", os.path.join(os.getcwd(), "data"))
    override = os.environ.get("CNEXUS_SEMANTIC_BUDGET_FILE", "").strip()
    if override:
        return override
    return os.path.join(base, "semantic_budget_state.json")


class SemanticBudgetStore:
    """Lightweight atomic state manager for SBSL EMA state."""

    def __init__(self, path: Optional[str] = None):
        self._path = path or default_budget_file()

    @property
    def path(self) -> str:
        return self._path

    def load(self) -> SemanticBudgetState:
        with _lock:
            if not os.path.isfile(self._path):
                return SemanticBudgetState()
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (OSError, json.JSONDecodeError):
                return SemanticBudgetState()
            if str(raw.get("version") or "") != _PERSIST_VERSION:
                return SemanticBudgetState.from_dict(raw.get("state") or raw)
            return SemanticBudgetState.from_dict(raw.get("state"))

    def save(self, state: SemanticBudgetState) -> None:
        directory = os.path.dirname(os.path.abspath(self._path))
        os.makedirs(directory, exist_ok=True)
        payload = {
            "version": _PERSIST_VERSION,
            "state": state.to_dict(),
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        with _lock:
            fd, tmp_path = tempfile.mkstemp(
                prefix=".semantic_budget_",
                suffix=".json",
                dir=directory or None,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(data)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_path, self._path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
