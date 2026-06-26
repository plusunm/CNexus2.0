"""Memory clear control API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .constitution_loader import default_constitution_dir
from .memory_foundation import (
    foundation_version_tree,
    list_foundation_versions,
    promote_block_in_store,
    upgrade_foundation_in_store,
)


@dataclass(frozen=True)
class MemoryControlHooks:
    audit_event: Callable[..., None]
    get_current_model_registry: Callable[[], Dict[str, Any]]
    default_model_registry: Callable[[], Dict[str, Any]]
    reset_engine_memory: Callable[[Dict[str, Any]], None]
    persist_file_path: Callable[[], str]
    append_runtime_log: Callable[..., None]
    persist_engine_state: Callable[[], None]
    persistence_status: Callable[[], Dict[str, Any]]
    cancel_scheduled_persist: Callable[[], None] = lambda: None
    persist_engine_state_fast: Callable[[], None] | None = None
    mutate_memory_store: Callable[..., Any] | None = None
    schedule_persist: Callable[[], None] | None = None
    constitution_dir: Callable[[], str] | None = None
    recompile_runtime: Callable[..., Dict[str, Any]] | None = None
    get_runtime_status: Callable[[], Dict[str, Any]] | None = None


class MemoryControlService:
    def __init__(self, hooks: MemoryControlHooks):
        self._hooks = hooks

    def clear(self, *, keep_models: bool = True, preserve_constitution: bool = True) -> Dict[str, Any]:
        self._hooks.cancel_scheduled_persist()
        self._hooks.audit_event(
            "memory.clear",
            {"keep_models": bool(keep_models), "preserve_constitution": bool(preserve_constitution)},
        )
        registry = (
            dict(self._hooks.get_current_model_registry())
            if keep_models
            else self._hooks.default_model_registry()
        )
        reset = self._hooks.reset_engine_memory
        try:
            reset(registry, preserve_constitution=preserve_constitution)
        except TypeError:
            reset(registry)
        path = self._hooks.persist_file_path()
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError as exc:
            self._hooks.append_runtime_log(
                f"删除快照文件失败 · {exc}",
                category="control_plane",
                level="warn",
            )
        fast_persist = self._hooks.persist_engine_state_fast
        if fast_persist is not None:
            fast_persist()
        else:
            self._hooks.persist_engine_state()
        self._hooks.append_runtime_log("记忆已手动清空", category="control_plane")
        return {
            "ok": True,
            "cleared": True,
            "keep_models": bool(keep_models),
            "preserve_constitution": bool(preserve_constitution),
            "persistence": self._hooks.persistence_status(),
        }

    def _require_store(self):
        if self._hooks.mutate_memory_store is None:
            raise RuntimeError("mutate_memory_store hook is not configured")
        return self._hooks.mutate_memory_store

    def _after_mutation(self) -> None:
        if self._hooks.schedule_persist is not None:
            self._hooks.schedule_persist()

    def promote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        block_id = str(data.get("block_id") or "").strip()
        if not block_id:
            return {"ok": False, "error": "block_id_required"}
        confirm = data.get("confirm", False)
        if isinstance(confirm, str):
            confirm = confirm.lower() in ("1", "true", "yes")
        target = str(data.get("memory_level") or "core")
        result = promote_block_in_store(
            self._require_store(),
            block_id=block_id,
            memory_level=target,
            confirm=bool(confirm),
        )
        if result.get("ok"):
            self._hooks.audit_event(
                "memory.promote",
                {"block_id": block_id, "memory_level": result.get("memory_level")},
            )
            self._after_mutation()
            self._hooks.append_runtime_log(
                f"记忆提升 · {block_id} → {result.get('memory_level')}",
                category="control_plane",
            )
        return result

    def foundation_upgrade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        block_id = str(data.get("block_id") or data.get("parent_block_id") or "").strip()
        content = str(data.get("content") or "")
        if not block_id:
            return {"ok": False, "error": "block_id_required"}
        result = upgrade_foundation_in_store(
            self._require_store(),
            block_id=block_id,
            content=content,
            source=str(data.get("source") or "api_upgrade"),
            version_label=str(data.get("version_label") or ""),
        )
        if result.get("ok"):
            self._hooks.audit_event("memory.foundation_upgrade", result)
            self._after_mutation()
            self._hooks.append_runtime_log(
                f"Foundation 升级 · v{result.get('memory_version')} · {result.get('block_id')}",
                category="control_plane",
            )
        return result

    def foundation_versions(self, *, constitution_key: Optional[str] = None) -> Dict[str, Any]:
        def read(store) -> Dict[str, Any]:
            versions = list_foundation_versions(list(store.blocks), constitution_key=constitution_key)
            active = [row for row in versions if row.get("active")]
            return {"ok": True, "versions": versions, "active_count": len(active), "total": len(versions)}

        return self._require_store()(read)

    def foundation_version_tree(self, *, constitution_key: Optional[str] = None) -> Dict[str, Any]:
        def read(store) -> Dict[str, Any]:
            trees = foundation_version_tree(list(store.blocks), constitution_key=constitution_key)
            return {"ok": True, "trees": trees, "count": len(trees)}

        return self._require_store()(read)

    def bootstrap_constitution(self, *, force: bool = False) -> Dict[str, Any]:
        """Legacy alias — recompiles Runtime constitution.bin (not Memory)."""
        if self._hooks.recompile_runtime is not None:
            status = self._hooks.recompile_runtime(force=force)
            return {"ok": bool(status.get("ok")), "runtime": status, "deprecated": "use POST /v1/runtime/recompile"}
        return {"ok": False, "error": "runtime_not_wired"}

    def runtime_status(self) -> Dict[str, Any]:
        if self._hooks.get_runtime_status is not None:
            return self._hooks.get_runtime_status()
        return {"ok": False, "error": "runtime_status_unavailable"}

    def migrate_protected_labels(self) -> Dict[str, Any]:
        try:
            from .constitution_loader import archive_legacy_runtime_memory_blocks, migrate_inferred_protected_blocks
        except ImportError:
            from cnexus_gateway.services.constitution_loader import (
                archive_legacy_runtime_memory_blocks,
                migrate_inferred_protected_blocks,
            )

        def apply(store):
            migrated = migrate_inferred_protected_blocks(store)
            archived = archive_legacy_runtime_memory_blocks(store)
            return {"ok": True, "migrated": migrated, "archived_runtime": archived}

        result = self._require_store()(apply)
        if result.get("migrated") or result.get("archived_runtime"):
            self._after_mutation()
        return result

    @staticmethod
    def resolve_constitution_dir(app_root: str) -> str:
        return default_constitution_dir(app_root)
