"""Foundation memory operations — promote, version upgrade, lineage listing."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .memory.protection import (
    block_memory_level,
    can_promote_level,
    foundation_doc_key,
    foundation_successor_block,
    level_priority,
    mark_block_superseded,
    normalize_memory_level,
    stamp_block_protection,
)

MutateStoreFn = Callable[[Callable[[Any], Any]], Any]


def list_foundation_versions(blocks: List[Dict[str, Any]], *, constitution_key: Optional[str] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    key_filter = str(constitution_key or "").strip()
    for block in blocks:
        if block_memory_level(block) != "foundation":
            continue
        data = block.get("data") or {}
        key = foundation_doc_key(block)
        if key_filter and key != key_filter:
            continue
        rows.append(
            {
                "block_id": block.get("block_id"),
                "constitution_key": key,
                "memory_level": "foundation",
                "memory_version": int(data.get("memory_version") or 1),
                "version_label": str(data.get("version_label") or f"v{int(data.get('memory_version') or 1)}"),
                "parent_version": data.get("parent_version"),
                "superseded": bool(data.get("superseded")),
                "active": not bool(data.get("superseded")),
                "title": str(data.get("filename") or key)[:120],
                "source": str(data.get("upgrade_source") or "ingest"),
                "timestamp": block.get("timestamp"),
            }
        )
    rows.sort(key=lambda row: (row["constitution_key"], -int(row["memory_version"] or 1)))
    return rows


def foundation_version_tree(blocks: List[Dict[str, Any]], *, constitution_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Build version branch tree per Foundation document key."""
    rows = list_foundation_versions(blocks, constitution_key=constitution_key)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["constitution_key"]), []).append(row)

    trees: List[Dict[str, Any]] = []
    for key, key_rows in grouped.items():
        nodes: Dict[str, Dict[str, Any]] = {}
        for row in key_rows:
            bid = str(row.get("block_id") or "")
            nodes[bid] = {**row, "children": []}
        roots: List[Dict[str, Any]] = []
        for row in key_rows:
            bid = str(row.get("block_id") or "")
            parent = str(row.get("parent_version") or "")
            node = nodes.get(bid)
            if not node:
                continue
            if parent and parent in nodes:
                nodes[parent]["children"].append(node)
            else:
                roots.append(node)
        active = [row for row in key_rows if row.get("active")]
        trees.append(
            {
                "constitution_key": key,
                "active_block_id": active[0]["block_id"] if active else None,
                "version_count": len(key_rows),
                "roots": roots,
                "versions": key_rows,
            }
        )
    trees.sort(key=lambda item: str(item.get("constitution_key") or ""))
    return trees


def promote_block_in_store(
    mutate_store: MutateStoreFn,
    *,
    block_id: str,
    memory_level: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    target = normalize_memory_level(memory_level)
    if level_priority(target) >= level_priority("project") and not confirm:
        return {
            "ok": False,
            "error": "confirmation_required",
            "message": "Promoting to project/core/foundation requires confirm=true",
        }

    def apply(store) -> Dict[str, Any]:
        found_idx = -1
        found: Optional[Dict[str, Any]] = None
        for idx, block in enumerate(store.blocks):
            if str(block.get("block_id")) == str(block_id):
                found_idx = idx
                found = block
                break
        if found is None:
            return {"ok": False, "error": "block_not_found", "block_id": block_id}

        current = block_memory_level(found)
        if not can_promote_level(current, target):
            return {
                "ok": False,
                "error": "invalid_promotion",
                "from": current,
                "to": target,
            }

        promoted = stamp_block_protection(dict(found), target)
        store.blocks[found_idx] = promoted
        data = promoted.get("data") or {}
        return {
            "ok": True,
            "block_id": block_id,
            "memory_level": data.get("memory_level"),
            "memory_version": data.get("memory_version"),
        }

    return mutate_store(apply)


def upgrade_foundation_in_store(
    mutate_store: MutateStoreFn,
    *,
    block_id: str,
    content: str,
    source: str = "api_upgrade",
    version_label: str = "",
) -> Dict[str, Any]:
    text = str(content or "").strip()
    if not text:
        return {"ok": False, "error": "empty_content"}

    def apply(store) -> Dict[str, Any]:
        parent_idx = -1
        parent: Optional[Dict[str, Any]] = None
        for idx, block in enumerate(store.blocks):
            if str(block.get("block_id")) == str(block_id):
                parent_idx = idx
                parent = block
                break
        if parent is None:
            return {"ok": False, "error": "block_not_found", "block_id": block_id}

        level = block_memory_level(parent)
        if level != "foundation":
            if can_promote_level(level, "foundation"):
                parent = stamp_block_protection(dict(parent), "foundation")
                store.blocks[parent_idx] = parent
            else:
                return {"ok": False, "error": "not_foundation", "memory_level": level}

        extra: Dict[str, Any] = {}
        label = str(version_label or "").strip()
        if label:
            extra["version_label"] = label
        superseded, child = foundation_successor_block(
            parent,
            text,
            source=source,
            extra_data=extra or None,
        )
        store.blocks[parent_idx] = superseded
        store.add(child)
        child_data = child.get("data") or {}
        return {
            "ok": True,
            "previous_block_id": block_id,
            "block_id": child.get("block_id"),
            "memory_version": child_data.get("memory_version"),
            "version_label": child_data.get("version_label"),
            "parent_version": child_data.get("parent_version"),
            "constitution_key": child_data.get("constitution_key"),
        }

    return mutate_store(apply)
