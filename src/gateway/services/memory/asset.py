"""MemoryAssetService — blob hydration + federated memory row search (P4-D)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ...state import EngineStateManager
from .query import MemoryQueryService

LoadFederatedSearchFn = Callable[[], Any]
GetPeerRegistryFn = Callable[[], Any]
GetDhtServiceFn = Callable[[], Any]
GetIdentityManagerFn = Callable[[], Any]
BuildSignedHeadersFn = Callable[..., Any]
BlobPresentFn = Callable[[str], bool]
PeerPullEnabledFn = Callable[[], bool]
EnsureLocalFn = Callable[..., Dict[str, Any]]
GetAssetProcessorFn = Callable[[], Any]


@dataclass(frozen=True)
class MemoryAssetHooks:
    load_federated_search_module: LoadFederatedSearchFn
    get_peer_registry: GetPeerRegistryFn
    get_dht_service: GetDhtServiceFn
    get_identity_manager: GetIdentityManagerFn
    build_signed_headers: BuildSignedHeadersFn
    blob_present: BlobPresentFn
    peer_pull_enabled: PeerPullEnabledFn
    ensure_local: EnsureLocalFn
    get_asset_processor: GetAssetProcessorFn = lambda: None


class MemoryAssetService:
    """Memory Domain asset port — recall hydration + unified block search rows."""

    def __init__(
        self,
        state: EngineStateManager,
        query: MemoryQueryService,
        hooks: MemoryAssetHooks,
    ):
        self._state = state
        self._query = query
        self._hooks = hooks

    def blob_present(self, asset_id: str) -> bool:
        return self._hooks.blob_present(str(asset_id or "").strip())

    def peer_pull_enabled(self) -> bool:
        return bool(self._hooks.peer_pull_enabled())

    def ensure_local_for_recall(self, asset_id: str, *, source_peer: str) -> Dict[str, Any]:
        return self._hooks.ensure_local(asset_id, source_peer=source_peer)

    def ensure_local(
        self,
        asset_id: str,
        *,
        source_peer: str = "",
        peer_host: str = "",
        auto_pull: Optional[bool] = None,
    ) -> Dict[str, Any]:
        return self._hooks.ensure_local(
            asset_id,
            source_peer=source_peer,
            peer_host=peer_host,
            auto_pull=auto_pull,
        )

    def _fed_module(self) -> Any:
        return self._hooks.load_federated_search_module()

    def trusted_peers(self) -> Set[str]:
        fed = self._fed_module()
        if not fed:
            return set()
        return fed.trusted_peer_pubkeys(self._hooks.get_peer_registry())

    def search_memory_rows(
        self,
        query: str,
        *,
        scope: str = "local",
        trusted: Optional[Set[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        trusted_set = trusted if trusted is not None else self.trusted_peers()

        def _read(engine: Dict[str, Any]) -> List[Dict[str, Any]]:
            return self._query.search_block_rows(
                engine["memory_store"],
                query,
                scope=scope,
                trusted=trusted_set,
                limit=limit,
            )

        return self._state.mutate(_read)

    def filter_rows_by_scope(
        self,
        rows: List[Dict[str, Any]],
        scope: str,
        trusted: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        fed = self._fed_module()
        if not fed:
            return list(rows)
        trusted_set = trusted if trusted is not None else self.trusted_peers()
        return fed.filter_rows_by_scope(rows, scope, trusted_set)

    def merge_search_hits(self, *groups: List[Dict[str, Any]], limit: int = 30) -> List[Dict[str, Any]]:
        fed = self._fed_module()
        if not fed:
            merged: List[Dict[str, Any]] = []
            for group in groups:
                merged.extend(group)
            return merged[:limit]
        return fed.merge_search_hits(*groups, limit=limit)

    def federated_semantic_search(
        self,
        local_hits: List[Dict[str, Any]],
        *,
        query: str,
        scope: str,
        kind: Optional[str] = None,
        limit: int = 20,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        fed = self._fed_module()
        if not fed:
            return list(local_hits), {}
        return fed.federated_semantic_search(
            local_hits,
            query=query,
            scope=scope,
            peer_registry=self._hooks.get_peer_registry(),
            dht_service=self._hooks.get_dht_service(),
            kind=kind,
            limit=limit,
            build_signed_headers=self._hooks.build_signed_headers,
            identity_manager=self._hooks.get_identity_manager(),
        )

    def enrich_asset_rows(self, hits: List[Dict[str, Any]], *, hydrate_missing: bool = False) -> List[Dict[str, Any]]:
        proc = self._hooks.get_asset_processor()
        if proc is None:
            for row in hits:
                row.setdefault("kind", "asset")
            return hits
        for row in hits:
            asset_id = str(row.get("asset_id") or "")
            meta = proc._read_meta(asset_id) or {}
            row["summary"] = meta.get("summary")
            row["desc"] = meta.get("desc")
            row["source_peer"] = meta.get("source_peer")
            row["local_blob"] = self.blob_present(asset_id)
            row.setdefault("kind", "asset")
            if (
                hydrate_missing
                and not row["local_blob"]
                and meta.get("source_peer")
                and self.peer_pull_enabled()
            ):
                pulled = self.ensure_local(asset_id, source_peer=str(meta.get("source_peer") or ""))
                row["pull"] = pulled
                row["local_blob"] = bool(pulled.get("ok"))
                if pulled.get("ok"):
                    meta = proc._read_meta(asset_id) or meta
                    row["summary"] = meta.get("summary")
                    row["desc"] = meta.get("desc")
        return hits

    def append_memory_to_hits(
        self,
        hits: List[Dict[str, Any]],
        query: str,
        *,
        scope: str,
        trusted: Optional[Set[str]] = None,
        limit: int,
    ) -> List[Dict[str, Any]]:
        if not str(query or "").strip():
            return hits
        memory_hits = self.search_memory_rows(query, scope=scope, trusted=trusted, limit=limit)
        return self.merge_search_hits(memory_hits, hits, limit=limit)

    def append_federated_remote(
        self,
        hits: List[Dict[str, Any]],
        query: str,
        *,
        scope: str,
        kind: Optional[str] = None,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        scope = str(scope or "local").strip().lower()
        if scope not in ("trusted", "network") or not str(query or "").strip():
            return hits, {}
        return self.federated_semantic_search(
            hits,
            query=query,
            scope=scope,
            kind=kind,
            limit=limit,
        )
