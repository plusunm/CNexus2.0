"""Catalog Layer service — P2.1 sync state machine."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib import error as urlerror

try:
    from protocol.models import BloomSummary, CatalogEntry, Commit, Graph
except ImportError:
    from cnexus_protocol.models import BloomSummary, CatalogEntry, Commit, Graph

from . import exchange_client
from .interest import CatalogInterest
from .namespace import normalize_namespace
from .store import CatalogStore
from .sync_fsm import CatalogSyncPhase, append_phase, build_sync_report


class CatalogService:
    """Catalog operations and peer sync FSM."""

    def __init__(self, store: CatalogStore):
        self.store = store

    def generation_payload(self) -> Dict[str, Any]:
        st = self.store.status()
        return {"ok": True, "generation": st["generation"], "graph_count": st["graph_count"]}

    def register_graph(
        self,
        graph: Graph,
        commit: Commit,
        *,
        manifest=None,
        chunk_hashes: Optional[Iterable[str]] = None,
        size: int = 0,
    ) -> CatalogEntry:
        chunks: tuple[str, ...] = ()
        root_hash = commit.root_hash
        if manifest is not None:
            if manifest.root_hash != commit.root_hash:
                raise ValueError("manifest.root_hash must match commit.root_hash")
            chunks = manifest.chunk_hashes()
            root_hash = manifest.root_hash
            chunk_hashes = chunks
        entry = CatalogEntry(
            graph_id=graph.graph_id,
            latest_commit_id=commit.commit_id,
            root_hash=root_hash,
            size=int(size),
            bloom_filter=b"",
            updated_at=time.time(),
            owner=graph.owner,
            topic=graph.metadata.topic,
            chunks=chunks if chunks else tuple(str(h).lower() for h in (chunk_hashes or ())),
        )
        return self.store.upsert_entry(entry, chunk_hashes=list(chunk_hashes or chunks or ()))

    def get_head(self, graph_id: str) -> Dict[str, Any]:
        head = self.store.get_head(graph_id)
        if head is None:
            return {"ok": False, "error": "graph_not_found"}, 404
        return {"ok": True, "head": head.to_dict()}, 200

    def get_bloom_summary(self, namespace: str = "catalog/system") -> Dict[str, Any]:
        summary = self.store.bloom_summary(namespace)
        return {"ok": True, "summary": summary.to_dict(), "generation": self.store.generation}

    def get_bloom_payload(self, namespace: str = "catalog/system") -> Dict[str, Any]:
        bloom = self.store.build_namespace_bloom(namespace)
        summary = self.store.bloom_summary(namespace)
        return {
            "ok": True,
            "bloom": bloom.to_base64(),
            "summary": summary.to_dict(),
            "generation": self.store.generation,
            "namespace": normalize_namespace(namespace),
        }

    def exchange_bloom(
        self,
        remote_bloom_b64: str = "",
        *,
        namespace: str = "catalog/system",
        remote_summary: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        local = self.store.build_namespace_bloom(namespace)
        summary = self.store.bloom_summary(namespace)
        interest_ids: List[str] = []
        if remote_bloom_b64:
            from .bloom_filter import BloomFilter

            remote = BloomFilter.from_base64(remote_bloom_b64)
            for graph_id in self.store.graph_ids():
                entry = self.store.get_entry(graph_id)
                if entry is None:
                    continue
                if not remote.might_contain(graph_id) and not remote.might_contain(entry.latest_commit_id):
                    interest_ids.append(graph_id)
        return {
            "ok": True,
            "bloom": local.to_base64(),
            "summary": summary.to_dict(),
            "generation": self.store.generation,
            "namespace": normalize_namespace(namespace),
            "remote_interest_graph_ids": interest_ids,
            "remote_summary_matched": bool(
                remote_summary
                and str(remote_summary.get("digest") or "") == summary.digest
            ),
        }

    def get_index_payload(
        self,
        *,
        since_commit_cursors: Optional[Mapping[str, str]] = None,
        interest: Optional[CatalogInterest] = None,
        namespace: str = "catalog/system",
        limit: int = 256,
    ) -> Dict[str, Any]:
        entries = self.store.list_entries(
            since_commit_cursors=since_commit_cursors,
            interest=interest,
            namespace=namespace,
            limit=limit,
        )
        return {
            "ok": True,
            "generation": self.store.generation,
            "entries": [entry.to_dict() for entry in entries],
            "count": len(entries),
            "cursors": dict(since_commit_cursors or {}),
        }

    def exchange_index(
        self,
        *,
        since_commit_cursors: Optional[Mapping[str, str]] = None,
        remote_entries: Optional[List[dict]] = None,
        interest: Optional[CatalogInterest] = None,
        namespace: str = "catalog/system",
        limit: int = 256,
    ) -> Dict[str, Any]:
        merged = 0
        if remote_entries:
            parsed = []
            for row in remote_entries:
                try:
                    parsed.append(CatalogEntry.from_dict(row))
                except Exception:
                    continue
            merged = self.store.merge_remote_entries(parsed)
        outbound = self.store.list_entries(
            since_commit_cursors=since_commit_cursors,
            interest=interest,
            namespace=namespace,
            limit=limit,
        )
        new_cursors = {e.graph_id: e.latest_commit_id for e in outbound}
        return {
            "ok": True,
            "generation": self.store.generation,
            "merged": merged,
            "entries": [entry.to_dict() for entry in outbound],
            "count": len(outbound),
            "commit_cursors": new_cursors,
        }

    def exchange_with_peer(
        self,
        peer_host: str,
        *,
        peer_id: str = "",
        interest: Optional[CatalogInterest] = None,
        namespace: str = "catalog/system",
    ) -> Dict[str, Any]:
        """P2.1 Catalog sync FSM: generation → summary → bloom → interest → index."""
        report = build_sync_report(peer_host=peer_host, peer_id=peer_id[:64] if peer_id else "")
        peer_state = self.store.get_peer_state(peer_id) if peer_id else {}
        local_gen = self.store.generation
        local_summary = self.store.bloom_summary(namespace)

        # ① Generation check
        append_phase(report, CatalogSyncPhase.GENERATION_CHECK, local=local_gen, remote_cached=peer_state.get("generation"))
        try:
            remote_gen_payload = exchange_client.fetch_generation(peer_host)
        except Exception as exc:
            append_phase(report, CatalogSyncPhase.ERROR, error=str(exc))
            report["error"] = str(exc)
            return report

        remote_gen = int(remote_gen_payload.get("generation") or 0)
        append_phase(report, CatalogSyncPhase.GENERATION_CHECK, remote=remote_gen)
        if peer_state.get("generation") == remote_gen and remote_gen > 0:
            append_phase(report, CatalogSyncPhase.GENERATION_SKIP, generation=remote_gen)
            report.update({"ok": True, "skipped": True, "reason": "generation_unchanged"})
            return report

        # ⑤ Bloom Summary check (before full bloom download)
        try:
            remote_summary_payload = exchange_client.fetch_bloom_summary(peer_host, namespace=namespace)
        except Exception as exc:
            append_phase(report, CatalogSyncPhase.ERROR, error=str(exc))
            report["error"] = str(exc)
            return report

        remote_summary_row = (remote_summary_payload.get("summary") or {}) if remote_summary_payload.get("ok") else {}
        remote_summary = BloomSummary.from_dict(remote_summary_row) if remote_summary_row else None
        append_phase(
            report,
            CatalogSyncPhase.SUMMARY_CHECK,
            local_digest=local_summary.digest,
            remote_digest=str(remote_summary_row.get("digest") or ""),
        )
        if (
            remote_summary
            and peer_state.get("summary_digest") == remote_summary.digest
            and local_summary.digest == remote_summary.digest
        ):
            append_phase(report, CatalogSyncPhase.SUMMARY_SKIP, digest=local_summary.digest)
            self.store.set_peer_state(peer_id, generation=remote_gen, summary_digest=local_summary.digest)
            report.update({"ok": True, "skipped": True, "reason": "summary_unchanged"})
            return report

        # Bloom exchange
        append_phase(report, CatalogSyncPhase.BLOOM_EXCHANGE, namespace=namespace)
        local_bloom = self.store.build_namespace_bloom(namespace).to_base64()
        try:
            bloom_resp = exchange_client.exchange_bloom(
                peer_host,
                local_bloom,
                namespace=namespace,
                summary=local_summary.to_dict(),
            )
        except urlerror.HTTPError as exc:
            append_phase(report, CatalogSyncPhase.ERROR, error=f"http_{exc.code}")
            report["error"] = f"http_{exc.code}"
            return report
        except Exception as exc:
            append_phase(report, CatalogSyncPhase.ERROR, error=str(exc))
            report["error"] = str(exc)
            return report

        if not bloom_resp.get("ok"):
            report["error"] = str(bloom_resp.get("error") or "bloom_failed")
            return report

        # ② Interest filter
        interest = interest or CatalogInterest.from_dict({})
        remote_interest = CatalogInterest.from_dict(bloom_resp.get("interest") or {})
        combined = CatalogInterest(
            topics=interest.topics or remote_interest.topics,
            owners=interest.owners or remote_interest.owners,
            graph_ids=interest.graph_ids or tuple(bloom_resp.get("remote_interest_graph_ids") or []),
        )
        append_phase(report, CatalogSyncPhase.INTEREST_FILTER, interest=combined.to_dict())

        # ③ Index exchange with since_commit_id cursors
        cursors = dict(peer_state.get("commit_cursors") or {})
        local_entries = [
            e.to_dict()
            for e in self.store.list_entries(
                since_commit_cursors=cursors,
                interest=combined if not combined.is_empty() else None,
                namespace=namespace,
                limit=256,
            )
        ]
        append_phase(report, CatalogSyncPhase.INDEX_EXCHANGE, outbound=len(local_entries))
        try:
            index_resp = exchange_client.exchange_index(
                peer_host,
                commit_cursors=cursors,
                entries=local_entries,
                interest=combined.to_dict(),
                namespace=namespace,
                limit=256,
            )
        except Exception as exc:
            append_phase(report, CatalogSyncPhase.ERROR, error=str(exc))
            report["error"] = str(exc)
            report["bloom_ok"] = True
            return report

        if not index_resp.get("ok"):
            report["error"] = str(index_resp.get("error") or "index_failed")
            report["bloom_ok"] = True
            return report

        remote_rows = index_resp.get("entries") or []
        merge_report = self.exchange_index(
            since_commit_cursors=cursors,
            remote_entries=remote_rows,
            interest=combined if not combined.is_empty() else None,
            namespace=namespace,
        )
        new_cursors = merge_report.get("commit_cursors") or {}
        if peer_id:
            self.store.set_peer_state(
                peer_id,
                generation=remote_gen,
                summary_digest=str(remote_summary_row.get("digest") or local_summary.digest),
                commit_cursors=new_cursors,
            )

        append_phase(report, CatalogSyncPhase.COMPLETE, merged=merge_report.get("merged"))
        report.update({
            "ok": True,
            "skipped": False,
            "local_generation": local_gen,
            "remote_generation": remote_gen,
            "merged_entries": merge_report.get("merged"),
            "received_entries": len(remote_rows),
            "sent_entries": len(local_entries),
            "commit_cursors": new_cursors,
            "need_p3": bool(merge_report.get("merged")),
        })
        if merge_report.get("merged"):
            report["next_phase"] = CatalogSyncPhase.NEED_P3.value
        return report

    def status(self) -> Dict[str, Any]:
        return {"ok": True, "catalog": self.store.status()}
