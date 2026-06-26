"""Active project switching and listing."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .memory.project import (
    default_active_project,
    is_valid_project_id,
    list_project_ids_from_blocks,
    normalize_active_project,
    normalize_lifecycle_id,
    normalize_project_id,
)

MutateEngineFn = Callable[[Callable[[Dict[str, Any]], Any]], Any]


@dataclass(frozen=True)
class ProjectControlHooks:
    mutate_engine: MutateEngineFn
    schedule_persist: Callable[[], None]
    audit_event: Callable[..., None]


class ProjectControlService:
    def get_active(self) -> Dict[str, Any]:
        def read(engine: Dict[str, Any]) -> Dict[str, Any]:
            active = normalize_active_project(engine.get("active_project"))
            return {"ok": True, "active_project": active}

        return self._hooks.mutate_engine(read)

    def set_active(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pid = normalize_project_id(data.get("project_id") or "default")
        if not is_valid_project_id(pid):
            return {"ok": False, "error": "invalid_project_id"}
        locked = data.get("lock", data.get("locked", False))
        if isinstance(locked, str):
            locked = locked.lower() in ("1", "true", "yes")
        lifecycle_id = normalize_lifecycle_id(data.get("lifecycle_id") or "")

        def apply(engine: Dict[str, Any]) -> Dict[str, Any]:
            active = {
                "project_id": pid,
                "name": str(data.get("name") or pid),
                "lifecycle_id": lifecycle_id,
                "locked": bool(locked),
                "locked_at": time.time() if locked else 0.0,
                "lock_session_id": str(data.get("session_id") or data.get("lock_session_id") or ""),
            }
            engine["active_project"] = normalize_active_project(active)
            return {"ok": True, "active_project": engine["active_project"]}

        result = self._hooks.mutate_engine(apply)
        if result.get("ok"):
            self._hooks.audit_event("project.active", result.get("active_project"))
            self._hooks.schedule_persist()
        return result

    def unlock(self) -> Dict[str, Any]:
        def apply(engine: Dict[str, Any]) -> Dict[str, Any]:
            current = normalize_active_project(engine.get("active_project"))
            current["locked"] = False
            current["locked_at"] = 0.0
            engine["active_project"] = current
            return {"ok": True, "active_project": current}

        result = self._hooks.mutate_engine(apply)
        self._hooks.schedule_persist()
        return result

    def list_projects(self) -> Dict[str, Any]:
        def read(engine: Dict[str, Any]) -> Dict[str, Any]:
            blocks = list(engine.get("memory_store", {}).blocks)
            projects = list_project_ids_from_blocks(blocks)
            active = normalize_active_project(engine.get("active_project"))
            return {"ok": True, "projects": projects, "active_project": active}

        return self._hooks.mutate_engine(read)

    def ensure_default(self) -> Dict[str, Any]:
        def apply(engine: Dict[str, Any]) -> Dict[str, Any]:
            if not engine.get("active_project"):
                engine["active_project"] = default_active_project()
            else:
                engine["active_project"] = normalize_active_project(engine.get("active_project"))
            return {"ok": True, "active_project": engine["active_project"]}

        return self._hooks.mutate_engine(apply)

    def __init__(self, hooks: ProjectControlHooks):
        self._hooks = hooks
