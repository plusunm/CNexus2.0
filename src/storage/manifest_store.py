"""ManifestStore — root_hash keyed manifest index (P3.5, no chunk bytes)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from protocol.models import Manifest
except ImportError:
    from cnexus_protocol.models import Manifest


class ManifestStore:
    """Persist Chunk Manifests keyed by root_hash with commit_id reverse index."""

    def __init__(self, storage_path: str | Path = "data/manifests.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self._commit_roots: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return
            self._manifests = dict(data.get("manifests") or {})
            self._commit_roots = dict(data.get("commit_roots") or {})
        except Exception:
            self._manifests = {}
            self._commit_roots = {}

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(
                {"manifests": self._manifests, "commit_roots": self._commit_roots},
                handle,
                ensure_ascii=False,
                indent=2,
            )

    def save(self, manifest: Manifest, *, commit_id: str = "") -> Manifest:
        if not manifest.verify_root():
            raise ValueError("manifest root_hash does not match chunk list")
        root = manifest.root_hash
        cid = str(commit_id or manifest.commit_id or "").strip().lower()
        with self._lock:
            self._manifests[root] = manifest.to_dict()
            if cid:
                self._commit_roots[cid] = root
            self._persist()
        return manifest

    def get(self, root_hash: str) -> Optional[Manifest]:
        root = str(root_hash or "").strip().lower()
        row = self._manifests.get(root)
        if not row:
            return None
        return Manifest.from_dict(row)

    def get_by_commit(self, commit_id: str) -> Optional[Manifest]:
        cid = str(commit_id or "").strip().lower()
        root = self._commit_roots.get(cid)
        if not root:
            return None
        return self.get(root)

    def list_roots(self) -> List[str]:
        with self._lock:
            return list(self._manifests.keys())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "manifest_count": len(self._manifests),
                "commit_bindings": len(self._commit_roots),
            }
