"""Boot-time loader for constitution/*.md — OS kernel documents."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .memory.protection import (
    block_memory_level,
    foundation_doc_key,
    foundation_successor_block,
    infer_memory_level_from_block,
    level_priority,
    stamp_block_protection,
)

MutateStoreFn = Callable[[Callable[[Any], Any]], Any]
TEXT_EXTENSIONS = frozenset({".md", ".markdown", ".txt"})


def default_constitution_dir(app_root: str) -> str:
    return os.path.join(app_root, "runtime", "constitution")


def default_foundation_dir(app_root: str) -> str:
    return os.path.join(app_root, "runtime", "foundation")


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _constitution_key_for_path(root: str, path: str) -> str:
    rel = os.path.relpath(path, root).replace("\\", "/")
    return f"constitution:{rel}"


def _foundation_key_for_path(root: str, path: str) -> str:
    rel = os.path.relpath(path, root).replace("\\", "/")
    return f"foundation:{rel}"


def _find_active_foundation(blocks: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_version = -1
    for block in blocks:
        if block_memory_level(block) != "foundation":
            continue
        data = block.get("data") or {}
        if data.get("superseded"):
            continue
        if foundation_doc_key(block) != key:
            continue
        version = int(data.get("memory_version") or 1)
        if version > best_version:
            best_version = version
            best = block
    return best


def migrate_inferred_protected_blocks(store: Any) -> int:
    """Stamp core/foundation levels on legacy blocks (e.g. user-fed manuals)."""
    updated = 0
    kept: List[Dict[str, Any]] = []
    for block in store.blocks:
        data = block.get("data") or {}
        if data.get("memory_level"):
            kept.append(block)
            continue
        inferred = infer_memory_level_from_block(block)
        if level_priority(inferred) >= level_priority("core"):
            kept.append(stamp_block_protection(dict(block), inferred))
            updated += 1
        else:
            kept.append(block)
    store.blocks = kept
    return updated


def archive_legacy_runtime_memory_blocks(store: Any) -> int:
    """Archive constitution blocks mistakenly written to Memory before Runtime split."""
    archived = 0
    kept: List[Dict[str, Any]] = []
    for block in store.blocks:
        data = dict(block.get("data") or {})
        should_archive = (
            data.get("upgrade_source") in ("constitution_boot", "runtime_compile")
            or str(data.get("constitution_key") or "").startswith("constitution:")
            or data.get("runtime_layer") in ("constitution", "policy")
        )
        if should_archive and not data.get("archived"):
            data["superseded"] = True
            data["archived"] = True
            data["archive_reason"] = "migrated_to_runtime"
            data["memory_level"] = "long_term"
            block = dict(block)
            block["data"] = data
            archived += 1
        kept.append(block)
    store.blocks = kept
    return archived


def bootstrap_constitution_dir(
    mutate_store: MutateStoreFn,
    constitution_dir: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Load or upgrade foundation blocks from constitution/*.md."""
    if not constitution_dir or not os.path.isdir(constitution_dir):
        return {"ok": True, "loaded": 0, "upgraded": 0, "migrated": 0, "skipped": 0, "dir": constitution_dir}

    files: List[str] = []
    for root, _dirs, names in os.walk(constitution_dir):
        for name in sorted(names):
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTENSIONS:
                continue
            files.append(os.path.join(root, name))

    if not files:
        return {"ok": True, "loaded": 0, "upgraded": 0, "migrated": 0, "skipped": 0, "dir": constitution_dir}

    report = {"loaded": 0, "upgraded": 0, "migrated": 0, "skipped": 0, "files": []}

    def apply(store) -> Dict[str, Any]:
        report["migrated"] = migrate_inferred_protected_blocks(store)
        blocks = list(store.blocks)

        for path in files:
            key = _constitution_key_for_path(constitution_dir, path)
            content = _read_text(path)
            if not content.strip():
                report["skipped"] += 1
                continue
            source_mtime = os.path.getmtime(path)
            active = _find_active_foundation(blocks, key)
            rel_name = os.path.relpath(path, constitution_dir).replace("\\", "/")

            if active is None:
                block_id = f"constitution-{int(time.time() * 1000)}-{report['loaded']}"
                new_block = stamp_block_protection(
                    {
                        "label": "semantic",
                        "block_id": block_id,
                        "data": {
                            "filename": rel_name,
                            "content": content[:20_000],
                            "constitution_key": key,
                            "memory_version": 1,
                            "upgrade_source": "constitution_boot",
                            "source_mtime": source_mtime,
                            "active": True,
                        },
                        "importance": 0.95,
                        "timestamp": time.time(),
                    },
                    "foundation",
                )
                store.add(new_block)
                blocks.append(new_block)
                report["loaded"] += 1
                report["files"].append({"file": rel_name, "action": "loaded", "block_id": block_id})
                continue

            active_data = active.get("data") or {}
            prev_mtime = float(active_data.get("source_mtime") or 0)
            if not force and prev_mtime >= source_mtime:
                report["skipped"] += 1
                continue

            superseded, child = foundation_successor_block(
                active,
                content,
                source="constitution_boot",
                extra_data={
                    "constitution_key": key,
                    "filename": rel_name,
                    "source_mtime": source_mtime,
                    "active": True,
                },
            )
            replaced = False
            for idx, block in enumerate(store.blocks):
                if str(block.get("block_id")) == str(active.get("block_id")):
                    store.blocks[idx] = superseded
                    replaced = True
                    break
            if replaced:
                store.add(child)
                blocks = list(store.blocks)
                report["upgraded"] += 1
                report["files"].append(
                    {
                        "file": rel_name,
                        "action": "upgraded",
                        "block_id": child.get("block_id"),
                        "version": (child.get("data") or {}).get("memory_version"),
                    }
                )

        return report

    out = mutate_store(apply)
    return {"ok": True, "dir": constitution_dir, **out}


def bootstrap_foundation_dir(
    mutate_store: MutateStoreFn,
    foundation_dir: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Load or upgrade shipped Foundation docs (user manual, guides) into Memory."""
    if not foundation_dir or not os.path.isdir(foundation_dir):
        return {"ok": True, "loaded": 0, "upgraded": 0, "migrated": 0, "skipped": 0, "dir": foundation_dir}

    files: List[str] = []
    for root, _dirs, names in os.walk(foundation_dir):
        for name in sorted(names):
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTENSIONS:
                continue
            files.append(os.path.join(root, name))

    if not files:
        return {"ok": True, "loaded": 0, "upgraded": 0, "migrated": 0, "skipped": 0, "dir": foundation_dir}

    report = {"loaded": 0, "upgraded": 0, "migrated": 0, "skipped": 0, "files": []}

    def apply(store) -> Dict[str, Any]:
        report["migrated"] = migrate_inferred_protected_blocks(store)
        blocks = list(store.blocks)

        for path in files:
            key = _foundation_key_for_path(foundation_dir, path)
            content = _read_text(path)
            if not content.strip():
                report["skipped"] += 1
                continue
            source_mtime = os.path.getmtime(path)
            active = _find_active_foundation(blocks, key)
            rel_name = os.path.relpath(path, foundation_dir).replace("\\", "/")

            if active is None:
                block_id = f"foundation-{int(time.time() * 1000)}-{report['loaded']}"
                new_block = stamp_block_protection(
                    {
                        "label": "semantic",
                        "block_id": block_id,
                        "data": {
                            "filename": rel_name,
                            "content": content[:20_000],
                            "constitution_key": key,
                            "memory_version": 1,
                            "upgrade_source": "foundation_boot",
                            "source_mtime": source_mtime,
                            "active": True,
                        },
                        "importance": 0.95,
                        "timestamp": time.time(),
                    },
                    "foundation",
                )
                store.add(new_block)
                blocks.append(new_block)
                report["loaded"] += 1
                report["files"].append({"file": rel_name, "action": "loaded", "block_id": block_id})
                continue

            active_data = active.get("data") or {}
            prev_mtime = float(active_data.get("source_mtime") or 0)
            if not force and prev_mtime >= source_mtime:
                report["skipped"] += 1
                continue

            superseded, child = foundation_successor_block(
                active,
                content,
                source="foundation_boot",
                extra_data={
                    "constitution_key": key,
                    "filename": rel_name,
                    "source_mtime": source_mtime,
                    "active": True,
                },
            )
            replaced = False
            for idx, block in enumerate(store.blocks):
                if str(block.get("block_id")) == str(active.get("block_id")):
                    store.blocks[idx] = superseded
                    replaced = True
                    break
            if replaced:
                store.add(child)
                blocks = list(store.blocks)
                report["upgraded"] += 1
                report["files"].append(
                    {
                        "file": rel_name,
                        "action": "upgraded",
                        "block_id": child.get("block_id"),
                        "version": (child.get("data") or {}).get("memory_version"),
                    }
                )

        return report

    out = mutate_store(apply)
    return {"ok": True, "dir": foundation_dir, **out}
