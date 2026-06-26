"""
Application Layer facade — cognition API without network awareness.

Application never knows DHT, Bloom, or Chunk transport.
It only expresses intent: publish / find / sync / merge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol

from .models import CatalogEntry, Commit, Graph


class CognitiveStore(Protocol):
    """Local persistence port (Storage Layer behind the facade)."""

    def get_graph(self, graph_id: str) -> Optional[Graph]: ...

    def get_commit(self, commit_id: str) -> Optional[Commit]: ...

    def save_graph(self, graph: Graph) -> None: ...

    def save_commit(self, commit: Commit) -> None: ...


class CatalogPort(Protocol):
    """Catalog Layer port — injected at runtime, not visible to app authors."""

    def publish_entry(self, entry: CatalogEntry) -> None: ...

    def find_entries(self, *, topic: str = "", owner: str = "") -> list[CatalogEntry]: ...


class CognitiveNetworkPort(Protocol):
    """Cognitive Layer port — sync/merge over commits, not handshake."""

    def pull_commits(self, graph_id: str, *, since_commit: str = "") -> list[Commit]: ...

    def push_commit(self, commit: Commit) -> dict[str, Any]: ...

    def merge_commits(self, graph_id: str, *, local_head: str, remote_head: str) -> Commit: ...


@dataclass
class CognitiveApplication:
    """
    Application Layer entry — Memory / Blueprint / Skill / Reflection bind here.
    Network stacks are adapters; this class stays transport-agnostic.
    """

    store: CognitiveStore
    catalog: Optional[CatalogPort] = None
    network: Optional[CognitiveNetworkPort] = None

    def publish(self, graph: Graph, commit: Commit, *, catalog_entry: Optional[CatalogEntry] = None) -> dict[str, Any]:
        self.store.save_graph(graph)
        self.store.save_commit(commit)
        if catalog_entry and self.catalog:
            self.catalog.publish_entry(catalog_entry)
        return {"ok": True, "graph_id": graph.graph_id, "commit_id": commit.commit_id}

    def find(self, *, graph_id: str = "", topic: str = "", owner: str = "") -> list[CatalogEntry]:
        if not self.catalog:
            return []
        if graph_id:
            # Catalog adapter may optimize single-graph lookup later.
            rows = self.catalog.find_entries(topic=topic, owner=owner)
            return [row for row in rows if row.graph_id == graph_id]
        return self.catalog.find_entries(topic=topic, owner=owner)

    def sync(self, graph_id: str, *, since_commit: str = "") -> dict[str, Any]:
        if not self.network:
            return {"ok": False, "error": "network_unconfigured"}
        commits = self.network.pull_commits(graph_id, since_commit=since_commit)
        for commit in commits:
            self.store.save_commit(commit)
        return {"ok": True, "graph_id": graph_id, "commits": [c.commit_id for c in commits]}

    def merge(
        self,
        graph_id: str,
        *,
        local_head: str,
        remote_head: str,
        merge_fn: Optional[Callable[[Commit, Commit], Commit]] = None,
    ) -> dict[str, Any]:
        if not self.network:
            return {"ok": False, "error": "network_unconfigured"}
        if merge_fn is not None:
            local = self.store.get_commit(local_head)
            remote = self.store.get_commit(remote_head)
            if local is None or remote is None:
                return {"ok": False, "error": "missing_commit"}
            merged = merge_fn(local, remote)
            self.store.save_commit(merged)
            return {"ok": True, "commit_id": merged.commit_id}
        merged = self.network.merge_commits(graph_id, local_head=local_head, remote_head=remote_head)
        self.store.save_commit(merged)
        return {"ok": True, "commit_id": merged.commit_id}
