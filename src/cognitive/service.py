"""Cognitive Layer — Commit DAG, Manifest publish, peer pull."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Union

try:
    from protocol.models import CatalogHead, Commit, Graph, Manifest, PublishTxn
except ImportError:
    from cnexus_protocol.models import CatalogHead, Commit, Graph, Manifest, PublishTxn

from . import exchange_client
from .commit_store import CommitStore
from .dag import commits_since, dag_payload


class CognitiveService:
    """P3 cognitive operations with P3.5 Manifest + PublishTxn atomic publish."""

    def __init__(
        self,
        store: CommitStore,
        catalog_service=None,
        *,
        manifest_store=None,
        txn_store=None,
        chunk_store=None,
        storage_service=None,
    ):
        self.store = store
        self.catalog = catalog_service
        self.manifests = manifest_store
        self.txn_store = txn_store
        self.chunks = chunk_store
        self.storage = storage_service

    def _resolve_manifest(
        self,
        commit: Commit,
        *,
        manifest: Optional[Manifest] = None,
        chunk_hashes: Optional[Iterable[str]] = None,
    ) -> Manifest:
        if manifest is not None:
            resolved = Manifest.from_dict(
                {
                    **manifest.to_dict(),
                    "graph_id": commit.graph_id,
                    "commit_id": commit.commit_id,
                }
            )
        elif chunk_hashes:
            resolved = Manifest.from_chunk_hashes(
                chunk_hashes,
                graph_id=commit.graph_id,
                commit_id=commit.commit_id,
            )
        elif self.manifests is not None:
            existing = self.manifests.get_by_commit(commit.commit_id) or self.manifests.get(commit.root_hash)
            if existing:
                resolved = existing
            else:
                resolved = Manifest.from_chunk_hashes((), graph_id=commit.graph_id, commit_id=commit.commit_id)
                if resolved.root_hash != commit.root_hash:
                    raise ValueError("manifest required: commit root_hash has no matching manifest")
        else:
            resolved = Manifest.from_chunk_hashes((), graph_id=commit.graph_id, commit_id=commit.commit_id)
        if resolved.root_hash != commit.root_hash:
            raise ValueError("commit.root_hash must equal manifest.root_hash")
        if not resolved.verify_root():
            raise ValueError("invalid manifest root_hash")
        return resolved

    def _ingest_verified_chunks(self, chunk_payloads: Optional[Iterable[Any]]) -> None:
        """Store chunks with bytes→hash verification before manifest/commit (P4)."""
        if not chunk_payloads or self.storage is None:
            return
        rows = []
        for item in chunk_payloads:
            if isinstance(item, dict):
                rows.append(item)
        if rows:
            result = self.storage.ingest_chunk_payloads(rows)
            if result.get("errors"):
                raise ValueError(f"chunk verify failed: {result['errors']}")

    def publish(
        self,
        graph: Graph,
        commit: Commit,
        *,
        manifest: Optional[Manifest] = None,
        chunk_hashes: Optional[Iterable[str]] = None,
        chunk_payloads: Optional[Iterable[Any]] = None,
        size: int = 0,
    ) -> Dict[str, Any]:
        """Atomically persist verified Chunks + Graph + Commit + Manifest + Catalog."""
        self._ingest_verified_chunks(chunk_payloads)
        resolved = self._resolve_manifest(commit, manifest=manifest, chunk_hashes=chunk_hashes)
        txn = None
        if self.txn_store is not None:
            txn = self.txn_store.begin(graph, commit, resolved, size=int(size))
        try:
            if txn is not None:
                self.txn_store.advance(txn.txn_id, PublishTxn.PHASE_PENDING_COMMIT)
            if self.manifests is not None:
                self.manifests.save(resolved, commit_id=commit.commit_id)
            self.store.save_graph(graph)
            self.store.save_commit(commit)
            if txn is not None:
                self.txn_store.advance(txn.txn_id, PublishTxn.PHASE_PENDING_CATALOG)
            entry = None
            if self.catalog is not None:
                entry = self.catalog.register_graph(
                    graph,
                    commit,
                    manifest=resolved,
                    chunk_hashes=resolved.chunk_hashes(),
                    size=int(size),
                )
            if txn is not None:
                self.txn_store.complete(txn.txn_id)
        except Exception:
            raise
        binding = None
        if self.storage is not None:
            binding, _ = self.storage.verify_manifest_binding(manifest=resolved)
        return {
            "ok": True,
            "graph_id": graph.graph_id,
            "commit_id": commit.commit_id,
            "head_commit": commit.commit_id,
            "root_hash": resolved.root_hash,
            "manifest": resolved.to_dict(),
            "catalog_entry": entry.to_dict() if entry else None,
            "txn_id": txn.txn_id if txn else None,
            "chunk_binding": binding,
        }

    def replay_txn(self, txn: PublishTxn) -> bool:
        """Resume a pending PublishTxn after crash."""
        graph = Graph.from_dict(txn.graph)
        commit = Commit.from_dict(txn.commit)
        manifest = Manifest.from_dict(txn.manifest)
        if txn.phase == PublishTxn.PHASE_PENDING_COMMIT:
            if self.manifests is not None:
                self.manifests.save(manifest, commit_id=commit.commit_id)
            self.store.save_graph(graph)
            self.store.save_commit(commit)
            if self.txn_store is not None:
                self.txn_store.advance(txn.txn_id, PublishTxn.PHASE_PENDING_CATALOG)
        if self.catalog is not None:
            head = self.store.get_head_commit_id(graph.graph_id)
            if head.lower() != commit.commit_id.lower():
                return False
            entry = self.catalog.store.get_entry(graph.graph_id)
            if entry and entry.latest_commit_id.lower() == commit.commit_id.lower():
                return True
            self.catalog.register_graph(
                graph,
                commit,
                manifest=manifest,
                chunk_hashes=manifest.chunk_hashes(),
                size=int(txn.size),
            )
        return True

    def heal_catalog_drift(self) -> int:
        """Register catalog rows for commits that exist locally but not in catalog index."""
        if self.catalog is None:
            return 0
        healed = 0
        for gid in self.store.list_graph_ids():
            head = self.store.get_head_commit_id(gid)
            if not head:
                continue
            entry = self.catalog.store.get_entry(gid)
            if entry and entry.latest_commit_id.lower() == head.lower():
                continue
            commit = self.store.get_commit(head)
            graph = self.store.get_graph(gid)
            if commit is None or graph is None:
                continue
            manifest = self.manifests.get_by_commit(head) if self.manifests else None
            chunk_hashes = manifest.chunk_hashes() if manifest else ()
            self.catalog.register_graph(
                graph,
                commit,
                manifest=manifest,
                chunk_hashes=chunk_hashes,
                size=int(entry.size if entry else 0),
            )
            healed += 1
        return healed

    def get_manifest(
        self,
        *,
        root_hash: str = "",
        commit_id: str = "",
    ) -> Union[tuple[Dict[str, Any], int], tuple[Dict[str, Any], int]]:
        if self.manifests is None:
            return {"ok": False, "error": "manifest_unavailable"}, 503
        manifest = None
        if commit_id:
            manifest = self.manifests.get_by_commit(commit_id)
        elif root_hash:
            manifest = self.manifests.get(root_hash)
        if manifest is None:
            return {"ok": False, "error": "manifest_not_found"}, 404
        return {"ok": True, "manifest": manifest.to_dict()}, 200

    def get_head(self, graph_id: str) -> Dict[str, Any]:
        gid = str(graph_id or "").strip().lower()
        head = self.store.get_head_commit_id(gid)
        if not head:
            if self.catalog is not None:
                return self.catalog.get_head(gid)
            return {"ok": False, "error": "graph_not_found"}, 404
        commit = self.store.get_commit(head)
        if commit is None:
            return {"ok": False, "error": "head_commit_missing"}, 404
        catalog_gen = 0
        head_generation = 1
        if self.catalog is not None:
            catalog_gen = self.catalog.store.generation
            entry = self.catalog.store.get_entry(gid)
            if entry:
                head_generation = entry.head_generation
        head_obj = CatalogHead(
            graph_id=gid,
            head_commit=commit.commit_id,
            head_generation=head_generation,
            root_hash=commit.root_hash,
            catalog_generation=catalog_gen,
            owner=commit.author,
            topic=(self.store.get_graph(gid) or Graph.from_dict({"graph_id": gid, "owner": commit.author})).metadata.topic,
        )
        payload: Dict[str, Any] = {"ok": True, "head": head_obj.to_dict()}
        if self.manifests is not None:
            manifest = self.manifests.get_by_commit(commit.commit_id) or self.manifests.get(commit.root_hash)
            if manifest:
                payload["manifest"] = manifest.to_dict()
        return payload, 200

    def get_dag(self, graph_id: str, *, limit: int = 512) -> Dict[str, Any]:
        gid = str(graph_id or "").strip().lower()
        head = self.store.get_head_commit_id(gid)
        if not head:
            return {"ok": False, "error": "graph_not_found"}, 404
        nodes = dag_payload(gid, head, self.store.get_commit, limit=limit)
        return {"ok": True, "graph_id": gid, "head_commit": head, "commits": nodes, "count": len(nodes)}, 200

    def get_commits_for_pull(
        self,
        graph_id: str,
        *,
        since_commit_id: str = "",
        limit: int = 256,
    ) -> Dict[str, Any]:
        gid = str(graph_id or "").strip().lower()
        head = self.store.get_head_commit_id(gid)
        if not head:
            return {"ok": False, "error": "graph_not_found"}, 404
        rows = commits_since(head, since_commit_id, self.store.get_commit, limit=limit)
        commit_rows = []
        for row in rows:
            item = row.to_dict()
            if self.manifests is not None:
                manifest = self.manifests.get_by_commit(row.commit_id) or self.manifests.get(row.root_hash)
                if manifest:
                    item["manifest"] = manifest.to_dict()
            commit_rows.append(item)
        return {
            "ok": True,
            "graph_id": gid,
            "head_commit": head,
            "since_commit_id": since_commit_id,
            "commits": commit_rows,
            "count": len(commit_rows),
        }, 200

    def ingest_commits(self, graph_id: str, commit_rows: List[dict]) -> Dict[str, Any]:
        gid = str(graph_id or "").strip().lower()
        parsed: List[Commit] = []
        manifests: List[Manifest] = []
        for row in commit_rows or []:
            try:
                item = dict(row)
                manifest_row = item.pop("manifest", None)
                commit = Commit.from_dict(item)
                if commit.graph_id != gid:
                    continue
                parsed.append(commit)
                if manifest_row and self.manifests is not None:
                    manifests.append(Manifest.from_dict({**manifest_row, "graph_id": gid, "commit_id": commit.commit_id}))
            except Exception:
                continue
        if not parsed:
            return {"ok": True, "ingested": 0, "graph_id": gid}
        parsed.sort(key=lambda c: c.timestamp)
        if self.manifests is not None:
            for manifest in manifests:
                self.manifests.save(manifest, commit_id=manifest.commit_id or "")
        self.store.save_commits(parsed)
        head = parsed[-1]
        graph = self.store.get_graph(gid)
        if graph is None and self.catalog is not None:
            entry = self.catalog.store.get_entry(gid)
            if entry is not None:
                try:
                    from protocol.models import GraphMetadata
                except ImportError:
                    from cnexus_protocol.models import GraphMetadata
                graph = Graph(
                    graph_id=gid,
                    owner=entry.owner,
                    metadata=GraphMetadata(topic=entry.topic),
                )
                self.store.save_graph(graph)
        manifest = self.manifests.get_by_commit(head.commit_id) if self.manifests else None
        if graph is not None and self.catalog is not None:
            self.catalog.register_graph(
                graph,
                head,
                manifest=manifest,
                chunk_hashes=manifest.chunk_hashes() if manifest else (),
            )
        return {
            "ok": True,
            "ingested": len(parsed),
            "graph_id": gid,
            "head_commit": head.commit_id,
        }

    def pull_from_peer(self, peer_host: str, graph_id: str, *, remote_head: str = "") -> Dict[str, Any]:
        """Pull HEAD → Commit DAG from trusted peer."""
        gid = str(graph_id or "").strip().lower()
        report: Dict[str, Any] = {"ok": False, "graph_id": gid, "peer_host": peer_host}
        local_head = self.store.get_head_commit_id(gid)
        try:
            if not remote_head:
                head_resp = exchange_client.fetch_head(peer_host, gid)
                if not head_resp.get("ok"):
                    report["error"] = str(head_resp.get("error") or "head_failed")
                    return report
                remote_head = str((head_resp.get("head") or {}).get("head_commit") or "")
            if not remote_head:
                report["error"] = "missing_remote_head"
                return report
            if local_head and local_head.lower() == remote_head.lower():
                report.update({"ok": True, "skipped": True, "reason": "already_at_head"})
                return report
            pull_resp = exchange_client.fetch_commits(
                peer_host,
                gid,
                since_commit_id=local_head,
                limit=256,
            )
        except Exception as exc:
            report["error"] = str(exc)
            return report
        if not pull_resp.get("ok"):
            report["error"] = str(pull_resp.get("pull_failed") or pull_resp.get("error") or "pull_failed")
            return report
        commits = pull_resp.get("commits") or []
        ingest = self.ingest_commits(gid, commits)
        report.update({
            "ok": True,
            "pulled": ingest.get("ingested", 0),
            "local_head_before": local_head,
            "remote_head": remote_head,
            "head_commit": ingest.get("head_commit"),
        })
        return report

    def sync_from_catalog_peer(self, peer_host: str, catalog_report: Dict[str, Any]) -> Dict[str, Any]:
        """After Catalog exchange, pull commits when catalog HEAD differs from local DAG."""
        if not catalog_report.get("ok"):
            return {"ok": False, "skipped": True, "reason": "catalog_not_ok"}
        if self.catalog is None:
            return {"ok": True, "pulls": [], "count": 0}
        results: List[Dict[str, Any]] = []
        for gid in self.catalog.store.graph_ids():
            entry = self.catalog.store.get_entry(gid)
            if entry is None:
                continue
            remote_head = entry.latest_commit_id
            local_head = self.store.get_head_commit_id(gid)
            if local_head and remote_head and local_head.lower() == remote_head.lower():
                continue
            results.append(self.pull_from_peer(peer_host, gid, remote_head=remote_head))
        return {"ok": True, "pulls": results, "count": len(results)}

    def status(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"ok": True, "cognitive": self.store.status()}
        if self.manifests is not None:
            payload["manifest"] = self.manifests.status()
        if self.txn_store is not None:
            payload["publish_txn"] = self.txn_store.status()
        if self.chunks is not None:
            payload["chunks"] = self.chunks.status()
        return payload
