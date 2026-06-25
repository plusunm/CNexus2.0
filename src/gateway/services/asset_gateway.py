"""Cognitive asset search, upload, ingest, and P2P blob operations."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from ..http.auth_gate import AuthGate
from .memory.asset import MemoryAssetService

JsonResponse = Tuple[Any, int]


@dataclass(frozen=True)
class AssetGatewayHooks:
    get_asset_processor: Callable[[], Any]
    get_vector_index: Callable[[], Any]
    get_clip_embedder: Callable[[], Any]
    get_asset_peer_sync: Callable[[], Any]
    get_asset_push_queue: Callable[[], Any]
    after_asset_indexed: Callable[..., None]
    schedule_persist: Callable[[], None]
    asset_peer_push_enabled: Callable[[], bool]


class AssetGatewayService:
    """Asset CRUD/search/upload — memory merge via MemoryAssetService."""

    def __init__(
        self,
        hooks: AssetGatewayHooks,
        auth: AuthGate,
        projection: Any,
        *,
        memory_assets: MemoryAssetService,
        touch_activity: Callable[[], None],
    ):
        self._hooks = hooks
        self._auth = auth
        self._projection = projection
        self._memory_assets = memory_assets
        self._touch_activity = touch_activity

    def check_auth(
        self,
        path: str,
        headers: Any,
        context: Dict[str, Any],
        *,
        method: str = "GET",
    ) -> Optional[JsonResponse]:
        return self._auth.check(path, headers, context, method=method)

    def get_processor(self) -> Any:
        return self._hooks.get_asset_processor()

    def blob_present(self, asset_id: str) -> bool:
        return self._memory_assets.blob_present(asset_id)

    def peer_pull_enabled(self) -> bool:
        return self._memory_assets.peer_pull_enabled()

    def ensure_local_for_recall(self, asset_id: str, *, source_peer: str) -> Dict[str, Any]:
        return self._memory_assets.ensure_local_for_recall(asset_id, source_peer=source_peer)

    def search(self, query: str, *, kind: str | None = None, limit: int = 20, scope: str = "local") -> JsonResponse:
        proc = self._hooks.get_asset_processor()
        if proc is None:
            return {"ok": False, "error": "asset_processor_unavailable"}, 503
        scope = str(scope or "local").strip().lower()
        assets = self._memory_assets
        trusted = assets.trusted_peers()
        cap = max(1, min(int(limit or 20), 100))
        hits = proc.search(query, kind=kind or None, limit=cap)
        hits = assets.enrich_asset_rows(hits)
        hits = assets.filter_rows_by_scope(hits, scope, trusted)
        hits = assets.append_memory_to_hits(hits, query, scope=scope, trusted=trusted, limit=cap)
        if scope in ("trusted", "network"):
            remote_rows, _ = assets.federated_semantic_search(
                [],
                query=query,
                scope=scope,
                kind=kind or None,
                limit=max(1, min(cap, 50)),
            )
            for row in remote_rows:
                row.setdefault("kind", "asset")
            hits = assets.merge_search_hits(hits, remote_rows, limit=cap)
        return {"ok": True, "query": query, "kind": kind, "scope": scope, "hits": hits, "count": len(hits)}, 200

    def search_semantic(
        self,
        query: str = "",
        *,
        kind: str | None = None,
        limit: int = 10,
        image_bytes: bytes | None = None,
        scope: str = "local",
    ) -> JsonResponse:
        idx = self._hooks.get_vector_index()
        if idx is None:
            return {"ok": False, "error": "vector_index_unavailable"}, 503
        scope = str(scope or "local").strip().lower()
        assets = self._memory_assets
        trusted = assets.trusted_peers()
        cap = max(1, min(int(limit or 10), 50))
        hits = idx.search(
            query,
            image_bytes=image_bytes,
            kind=kind or None,
            limit=cap,
        )
        hits = assets.enrich_asset_rows(hits, hydrate_missing=True)
        federated_report: Dict[str, Any] = {}
        hits = assets.filter_rows_by_scope(hits, scope, trusted)
        if query and not image_bytes:
            hits = assets.append_memory_to_hits(hits, query, scope=scope, trusted=trusted, limit=cap)
        if scope in ("trusted", "network") and query and not image_bytes:
            hits, federated_report = assets.append_federated_remote(
                hits,
                query,
                scope=scope,
                kind=kind or None,
                limit=cap,
            )
        clip = self._hooks.get_clip_embedder()
        return {
            "ok": True,
            "query": query,
            "kind": kind,
            "scope": scope,
            "mode": "semantic_image" if image_bytes else "semantic",
            "hits": hits,
            "count": len(hits),
            "index": idx.status(),
            "cross_modal": bool(clip and getattr(clip, "unified_space", False)),
            "federated": federated_report,
        }, 200

    def push_queue(self, *, process: bool = False, limit: int = 20) -> JsonResponse:
        queue = self._hooks.get_asset_push_queue()
        if queue is None:
            return {"ok": False, "error": "push_queue_unavailable"}, 503
        if process:
            report = queue.process_pending(limit=max(1, min(int(limit or 20), 100)))
            return {"ok": True, **report, "queue": queue.status()}, 200
        return {"ok": True, "queue": queue.status()}, 200

    def reindex(self) -> JsonResponse:
        proc = self._hooks.get_asset_processor()
        idx = self._hooks.get_vector_index()
        if proc is None or idx is None:
            return {"ok": False, "error": "asset_index_unavailable"}, 503
        metas = proc.list_assets(limit=500)

        def _read_blob(asset_id: str, meta: dict):
            blob, _, _ = proc.read_raw(asset_id)
            return blob

        report = idx.rebuild_all(metas, read_blob_fn=_read_blob)
        return {"ok": True, **report, "index": idx.status()}, 200

    def list_assets(self, *, kind: str | None = None, limit: int = 50) -> JsonResponse:
        proc = self._hooks.get_asset_processor()
        if proc is None:
            return {"ok": False, "error": "asset_processor_unavailable"}, 503
        rows = proc.list_assets(kind=kind or None, limit=max(1, min(int(limit or 50), 200)))
        return {"ok": True, "assets": rows, "count": len(rows)}, 200

    def get_asset(self, asset_id: str, *, include_content: bool = False) -> JsonResponse:
        proc = self._hooks.get_asset_processor()
        if proc is None:
            return {"ok": False, "error": "asset_processor_unavailable"}, 503
        return proc.get_asset(asset_id, include_content=include_content)

    def receive(self, data: Dict[str, Any], headers: Any) -> JsonResponse:
        sync = self._hooks.get_asset_peer_sync()
        if sync is None:
            return {"ok": False, "error": "peer_sync_unavailable"}, 503
        peer_pubkey = ""
        if hasattr(headers, "get"):
            peer_pubkey = str(headers.get("X-CNexus-Pubkey") or headers.get("x-cnexus-pubkey") or "")
        result = sync.receive(data or {}, peer_pubkey=peer_pubkey)
        if result.get("ok"):
            self._hooks.after_asset_indexed(result)
            self._hooks.schedule_persist()
        code = 200 if result.get("ok") else 400
        return result, code

    def pull(self, asset_id: str, *, source_peer: str = "", peer_host: str = "") -> JsonResponse:
        asset_id = str(asset_id or "").strip()
        if not asset_id:
            return {"ok": False, "error": "missing_asset_id"}, 400
        proc = self._hooks.get_asset_processor()
        if proc is None:
            return {"ok": False, "error": "asset_processor_unavailable"}, 503
        meta = proc._read_meta(asset_id) or {}
        peer = str(source_peer or meta.get("source_peer") or "").strip()
        host = str(peer_host or meta.get("peer_host") or "").strip()
        report = self._memory_assets.ensure_local(
            asset_id,
            source_peer=peer,
            peer_host=host,
            auto_pull=True,
        )
        code = 200 if report.get("ok") else 404 if report.get("error") == "blob_missing" else 502
        return report, code

    def push(self, asset_id: str) -> JsonResponse:
        sync = self._hooks.get_asset_peer_sync()
        if sync is None:
            return {"ok": False, "error": "peer_sync_unavailable"}, 503
        asset_id = str(asset_id or "").strip()
        if not asset_id:
            return {"ok": False, "error": "missing_asset_id"}, 400
        return sync.push_asset(asset_id), 200

    def ingest_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._touch_activity()
        return self._projection.ingest_image(data)

    def ingest_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._touch_activity()
        return self._projection.ingest_code(data)

    def upload_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._touch_activity()
        content = data.get("content") or data.get("source") or ""
        filename = data.get("filename") or data.get("file_name") or "snippet.py"
        proc = self._hooks.get_asset_processor()
        if proc is None:
            return {"ok": False, "error": "asset_processor_unavailable"}
        result = proc.process_code(str(content), str(filename))
        if result.get("ok") and bool(data.get("project")):
            result["projection"] = self._projection.ingest_code({"content": content, "file_name": filename})
        if result.get("ok"):
            if self._hooks.asset_peer_push_enabled() and result.get("status") == "indexed":
                result["peer_push"] = "scheduled"
            self._hooks.after_asset_indexed(result)
            self._hooks.schedule_persist()
        return result

    def upload_image(
        self,
        data: Dict[str, Any],
        *,
        binary: bytes | None = None,
        filename: str = "image.jpg",
    ) -> Dict[str, Any]:
        self._touch_activity()
        proc = self._hooks.get_asset_processor()
        if proc is None:
            return {"ok": False, "error": "asset_processor_unavailable"}

        raw = binary
        if raw is None:
            image_b64 = data.get("image_base64") or data.get("image") or ""
            raw_str = str(image_b64 or "").strip()
            if "," in raw_str:
                raw_str = raw_str.split(",", 1)[1]
            if raw_str:
                try:
                    raw = base64.b64decode(raw_str)
                except Exception:
                    return {"ok": False, "error": "invalid_image_base64"}
        if not raw:
            return {"ok": False, "error": "missing_image_data"}

        name = data.get("filename") or data.get("file_name") or filename
        result = proc.process_image(raw, str(name))
        if result.get("ok") and bool(data.get("project")):
            result["projection"] = self._projection.ingest_image(
                {"image_base64": base64.b64encode(raw).decode("ascii")}
            )
        if result.get("ok"):
            if self._hooks.asset_peer_push_enabled() and result.get("status") == "indexed":
                result["peer_push"] = "scheduled"
            self._hooks.after_asset_indexed(result)
            self._hooks.schedule_persist()
        return result
