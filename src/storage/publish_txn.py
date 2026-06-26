"""PublishTxn journal — atomic Commit + Manifest + Catalog with crash recovery."""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from protocol.models import Commit, Graph, Manifest, PublishTxn
except ImportError:
    from cnexus_protocol.models import Commit, Graph, Manifest, PublishTxn


class PublishTxnStore:
    """Write-ahead journal for publish atomicity across CommitStore and Catalog."""

    def __init__(self, storage_path: str | Path = "data/publish_txn.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return
            self._pending = dict(data.get("pending") or {})
        except Exception:
            self._pending = {}

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump({"pending": self._pending}, handle, ensure_ascii=False, indent=2)

    def begin(
        self,
        graph: Graph,
        commit: Commit,
        manifest: Manifest,
        *,
        size: int = 0,
    ) -> PublishTxn:
        txn = PublishTxn(
            txn_id=uuid.uuid4().hex,
            phase=PublishTxn.PHASE_PENDING_COMMIT,
            graph=graph.to_dict(),
            commit=commit.to_dict(),
            manifest=manifest.to_dict(),
            size=int(size),
        )
        with self._lock:
            self._pending[txn.txn_id] = txn.to_dict()
            self._persist()
        return txn

    def advance(self, txn_id: str, phase: str) -> None:
        with self._lock:
            row = dict(self._pending.get(str(txn_id)) or {})
            if not row:
                return
            row["phase"] = str(phase)
            self._pending[str(txn_id)] = row
            self._persist()

    def complete(self, txn_id: str) -> None:
        with self._lock:
            self._pending.pop(str(txn_id), None)
            self._persist()

    def list_pending(self) -> List[PublishTxn]:
        with self._lock:
            rows = list(self._pending.values())
        return [PublishTxn.from_dict(row) for row in rows]

    def recover(self, cognitive_service) -> Dict[str, Any]:
        """
        Replay incomplete publishes and heal Commit/Catalog drift.
        Called once at service startup.
        """
        report: Dict[str, Any] = {"recovered_txns": 0, "healed_catalog": 0, "errors": []}
        for txn in self.list_pending():
            try:
                if cognitive_service.replay_txn(txn):
                    self.complete(txn.txn_id)
                    report["recovered_txns"] += 1
            except Exception as exc:
                report["errors"].append({"txn_id": txn.txn_id, "error": str(exc)})
        healed = cognitive_service.heal_catalog_drift()
        report["healed_catalog"] = healed
        return report

    def status(self) -> Dict[str, Any]:
        with self._lock:
            pending = list(self._pending.values())
        return {"pending_count": len(pending), "pending": pending}
