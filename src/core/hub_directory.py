"""Hub rendezvous directory — pubkey → reachable host/endpoints."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class HubDirectory:
    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._peers: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(self._peers, handle, ensure_ascii=False, indent=2)

    def register(
        self,
        pubkey: str,
        host: str,
        *,
        endpoints: Optional[List[str]] = None,
        label: str = "",
    ) -> dict:
        pubkey = str(pubkey or "").strip().lower()
        if not pubkey:
            raise ValueError("pubkey required")
        host = str(host or "").strip().rstrip("/")
        eps = [str(u or "").strip().rstrip("/") for u in (endpoints or []) if str(u or "").strip()]
        if host and host not in eps:
            eps.insert(0, host)
        if not host and eps:
            host = eps[0]
        row = {
            "pubkey": pubkey,
            "host": host,
            "endpoints": eps,
            "label": str(label or "").strip(),
            "registered_at": time.time(),
            "last_seen": time.time(),
        }
        with self._lock:
            prev = dict(self._peers.get(pubkey) or {})
            if prev.get("registered_at"):
                row["registered_at"] = prev["registered_at"]
            if not row["label"] and prev.get("label"):
                row["label"] = prev["label"]
            self._peers[pubkey] = row
            self._persist()
        return dict(row)

    def resolve(self, pubkey: str) -> Optional[dict]:
        pubkey = str(pubkey or "").strip().lower()
        if not pubkey:
            return None
        with self._lock:
            row = dict(self._peers.get(pubkey) or {})
        if not row:
            return None
        host = str(row.get("host") or "").strip()
        if not host:
            eps = list(row.get("endpoints") or [])
            host = str(eps[0] if eps else "").strip()
        if not host:
            return None
        return {
            "pubkey": pubkey,
            "host": host,
            "endpoints": list(row.get("endpoints") or []),
            "label": row.get("label") or "",
            "last_seen": row.get("last_seen"),
        }

    def list_peers(self, *, limit: int = 256) -> List[dict]:
        with self._lock:
            rows = [dict(v) for v in self._peers.values()]
        rows.sort(key=lambda r: float(r.get("last_seen") or 0), reverse=True)
        return rows[: max(1, int(limit))]
