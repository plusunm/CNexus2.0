"""CommitStore — local Graph + Commit DAG persistence."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from protocol.models import Commit, Graph
except ImportError:
    from cnexus_protocol.models import Commit, Graph


class CommitStore:
    """Persistent cognitive graph container and commit DAG."""

    def __init__(self, storage_path: str | Path = "data/cognitive.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._commits: Dict[str, Dict[str, Any]] = {}
        self._heads: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return
            self._graphs = dict(data.get("graphs") or {})
            self._commits = dict(data.get("commits") or {})
            self._heads = dict(data.get("heads") or {})
        except Exception:
            self._graphs = {}
            self._commits = {}
            self._heads = {}

    def _persist(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(
                {"graphs": self._graphs, "commits": self._commits, "heads": self._heads},
                handle,
                ensure_ascii=False,
                indent=2,
            )

    def get_graph(self, graph_id: str) -> Optional[Graph]:
        row = self._graphs.get(str(graph_id or "").strip().lower())
        if not row:
            return None
        return Graph.from_dict(row)

    def get_commit(self, commit_id: str) -> Optional[Commit]:
        row = self._commits.get(str(commit_id or "").strip().lower())
        if not row:
            row = self._commits.get(str(commit_id or ""))
        if not row:
            return None
        return Commit.from_dict(row)

    def get_head_commit_id(self, graph_id: str) -> str:
        gid = str(graph_id or "").strip().lower()
        return str(self._heads.get(gid) or "")

    def save_graph(self, graph: Graph) -> None:
        gid = graph.graph_id
        with self._lock:
            self._graphs[gid] = graph.to_dict()
            self._persist()

    def save_commit(self, commit: Commit) -> None:
        with self._lock:
            self._commits[commit.commit_id] = commit.to_dict()
            self._heads[commit.graph_id] = commit.commit_id
            self._persist()

    def save_commits(self, commits: List[Commit]) -> int:
        if not commits:
            return 0
        with self._lock:
            for commit in commits:
                self._commits[commit.commit_id] = commit.to_dict()
                self._heads[commit.graph_id] = commit.commit_id
            self._persist()
        return len(commits)

    def list_graph_ids(self) -> List[str]:
        with self._lock:
            return list(self._graphs.keys())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "graph_count": len(self._graphs),
                "commit_count": len(self._commits),
                "heads": dict(self._heads),
            }
