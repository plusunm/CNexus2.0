"""L3 Project binding — project_id on blocks, active_project lock in engine state."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Mapping, Optional

from .protection import block_memory_level, level_priority, stamp_block_protection

_PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def normalize_project_id(raw: Any) -> str:
    value = str(raw or "").strip().lower().replace(" ", "-")
    value = re.sub(r"[^a-z0-9._-]", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:64]


def normalize_lifecycle_id(raw: Any) -> str:
    value = str(raw or "").strip().lower().replace(" ", "-")
    value = re.sub(r"[^a-z0-9._-]", "-", value)
    return value[:64]


def is_valid_project_id(project_id: str) -> bool:
    return bool(project_id) and bool(_PROJECT_ID_RE.match(project_id))


def block_project_id(block: Mapping[str, Any]) -> str:
    data = block.get("data") or {}
    return str(data.get("project_id") or "")


def block_lifecycle_id(block: Mapping[str, Any]) -> str:
    data = block.get("data") or {}
    return str(data.get("lifecycle_id") or "")


def attach_project_scope(
    block: Dict[str, Any],
    *,
    project_id: str,
    lifecycle_id: str = "",
) -> Dict[str, Any]:
    """Stamp project_id / lifecycle_id without changing memory_level."""
    pid = normalize_project_id(project_id)
    if not is_valid_project_id(pid):
        return dict(block)
    out = dict(block)
    data = dict(out.get("data") or {})
    data["project_id"] = pid
    if lifecycle_id:
        data["lifecycle_id"] = normalize_lifecycle_id(lifecycle_id)
    out["data"] = data
    return out


def stamp_project_binding(
    block: Dict[str, Any],
    *,
    project_id: str,
    lifecycle_id: str = "",
    memory_level: Optional[str] = None,
) -> Dict[str, Any]:
    pid = normalize_project_id(project_id)
    if not is_valid_project_id(pid):
        raise ValueError(f"invalid project_id: {project_id}")
    out = dict(block)
    data = dict(out.get("data") or {})
    data["project_id"] = pid
    if lifecycle_id:
        data["lifecycle_id"] = normalize_lifecycle_id(lifecycle_id)
    out["data"] = data
    level = memory_level or data.get("memory_level") or block_memory_level(out)
    if level_priority(str(level)) < level_priority("project"):
        level = "project"
    return stamp_block_protection(out, str(level))


def default_active_project() -> Dict[str, Any]:
    return {
        "project_id": "default",
        "name": "Default Project",
        "lifecycle_id": "",
        "locked": False,
        "locked_at": 0.0,
        "lock_session_id": "",
    }


def normalize_active_project(raw: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    base = default_active_project()
    if not raw:
        return base
    pid = normalize_project_id(raw.get("project_id") or base["project_id"])
    if not is_valid_project_id(pid):
        pid = base["project_id"]
    locked = bool(raw.get("locked"))
    return {
        "project_id": pid,
        "name": str(raw.get("name") or pid),
        "lifecycle_id": normalize_lifecycle_id(raw.get("lifecycle_id") or ""),
        "locked": locked,
        "locked_at": float(raw.get("locked_at") or (time.time() if locked else 0)),
        "lock_session_id": str(raw.get("lock_session_id") or ""),
    }


def block_visible_for_active_project(block: Mapping[str, Any], active_project: Optional[Mapping[str, Any]]) -> bool:
    """When active_project.locked, L3 project blocks must match project_id."""
    active = normalize_active_project(active_project) if active_project else None
    if not active or not active.get("locked"):
        return True
    level = block_memory_level(block)
    if level_priority(level) > level_priority("project"):
        return True
    if level_priority(level) < level_priority("project"):
        return True
    pid = str(active.get("project_id") or "")
    block_pid = block_project_id(block)
    if not block_pid:
        return False
    if block_pid != pid:
        return False
    lifecycle = str(active.get("lifecycle_id") or "")
    if lifecycle and block_lifecycle_id(block) and block_lifecycle_id(block) != lifecycle:
        return False
    return True


def spec_visible_for_active_project(spec: Mapping[str, Any], active_project: Optional[Mapping[str, Any]]) -> bool:
    level = str(spec.get("memory_level") or "long_term")
    pseudo = {
        "data": {
            "project_id": spec.get("project_id"),
            "lifecycle_id": spec.get("lifecycle_id"),
            "memory_level": level,
        }
    }
    return block_visible_for_active_project(pseudo, active_project)


def list_project_ids_from_blocks(blocks: list) -> list[Dict[str, Any]]:
    counts: Dict[str, Dict[str, Any]] = {}
    for block in blocks:
        pid = block_project_id(block)
        if not pid:
            continue
        level = block_memory_level(block)
        row = counts.setdefault(
            pid,
            {"project_id": pid, "block_count": 0, "foundation_count": 0, "project_count": 0},
        )
        row["block_count"] += 1
        if level == "foundation":
            row["foundation_count"] += 1
        if level == "project":
            row["project_count"] += 1
        lifecycle = block_lifecycle_id(block)
        if lifecycle:
            row["lifecycle_id"] = lifecycle
    return sorted(counts.values(), key=lambda item: (-int(item["block_count"]), item["project_id"]))
