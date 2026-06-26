"""Memory protection levels — L0 temporary through L3 foundation (认知宪法)."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

import time

_LEVEL_ALIASES = {
    "l0": "scratch",
    "scratch": "scratch",
    "conversation": "scratch",
    "l1": "temporary",
    "temporary": "temporary",
    "temp": "temporary",
    "l1": "long_term",
    "long_term": "long_term",
    "long-term": "long_term",
    "persistent": "long_term",
    "l2": "core",
    "core": "core",
    "l3": "project",
    "project": "project",
    "l4": "foundation",
    "foundation": "foundation",
    "constitution": "foundation",
}

LEVEL_PRIORITY: Dict[str, int] = {
    "scratch": 0,
    "temporary": 1,
    "long_term": 2,
    "project": 3,
    "core": 4,
    "foundation": 5,
}

LEVEL_POLICY: Dict[str, Dict[str, bool]] = {
    "scratch": {
        "editable": True,
        "deletable": True,
        "append_only": False,
        "prune": True,
        "clear": True,
    },
    "temporary": {
        "editable": True,
        "deletable": True,
        "append_only": False,
        "prune": True,
        "clear": True,
    },
    "long_term": {
        "editable": True,
        "deletable": True,
        "append_only": False,
        "prune": True,
        "clear": True,
    },
    "project": {
        "editable": True,
        "deletable": False,
        "append_only": False,
        "prune": False,
        "clear": False,
    },
    "core": {
        "editable": False,
        "deletable": False,
        "append_only": False,
        "prune": False,
        "clear": False,
    },
    "foundation": {
        "editable": False,
        "deletable": False,
        "append_only": True,
        "prune": False,
        "clear": False,
    },
}

CONSTITUTION_FILENAME_HINTS = (
    "用户手册",
    "实战指南",
    "workflow",
    "skill",
    "prompt模板",
    "prompt_template",
    "官方",
)

FOUNDATION_CONTENT_HINTS = (
    "cnexus",
    "用户手册",
    "实战指南",
    "foundation memory",
    "认知演化链",
)

# Runtime constitution sources must never enter Memory as Foundation.
RUNTIME_SOURCE_MARKERS = (
    "cognitive_constitution",
    "runtime_contract",
    "product_philosophy",
    "reasoning_policy",
    "memory_merge_policy",
    "workflow_policy",
    "constitution:",
)


def normalize_memory_level(raw: Any) -> str:
    key = str(raw or "long_term").strip().lower().replace(" ", "_")
    return _LEVEL_ALIASES.get(key, "long_term")


def level_policy(level: str) -> Dict[str, bool]:
    return dict(LEVEL_POLICY.get(normalize_memory_level(level), LEVEL_POLICY["long_term"]))


def level_priority(level: str) -> int:
    return LEVEL_PRIORITY.get(normalize_memory_level(level), 1)


def infer_memory_level_from_ingest(filename: str, content: str = "", *, scratch: bool = False) -> str:
    if scratch:
        return "scratch"
    fn = str(filename or "").lower()
    for marker in RUNTIME_SOURCE_MARKERS:
        if marker.lower() in fn:
            return "long_term"
    text = str(content or "")[:4000].lower()
    for hint in CONSTITUTION_FILENAME_HINTS:
        if hint.lower() in fn:
            return "foundation"
    hits = sum(1 for hint in FOUNDATION_CONTENT_HINTS if hint.lower() in text)
    if hits >= 2:
        return "foundation"
    if any(token in fn for token in ("手册", "manual", "guide", "指南")):
        return "core"
    if any(token in fn for token in ("project", "项目", "timeline", "workflow", "decision")):
        return "project"
    return "long_term"


def infer_memory_level_from_block(block: Mapping[str, Any]) -> str:
    data = block.get("data") or {}
    label = str(block.get("label") or "")
    if label == "persona":
        return "core"
    return infer_memory_level_from_ingest(
        str(data.get("filename") or data.get("label") or ""),
        str(data.get("content") or ""),
    )


def block_memory_level(block: Mapping[str, Any]) -> str:
    data = block.get("data") or {}
    raw = data.get("memory_level") or data.get("protection_level") or block.get("memory_level")
    if raw:
        return normalize_memory_level(raw)
    return infer_memory_level_from_block(block)


def stamp_block_protection(block: Dict[str, Any], level: Optional[str] = None) -> Dict[str, Any]:
    """Attach memory_level and policy flags to a block."""
    out = dict(block)
    data = dict(out.get("data") or {})
    lvl = normalize_memory_level(level or data.get("memory_level") or block_memory_level(out))
    policy = level_policy(lvl)
    data["memory_level"] = lvl
    data.setdefault("memory_version", int(data.get("memory_version") or 1))
    data["editable"] = policy["editable"]
    data["deletable"] = policy["deletable"]
    data["append_only"] = policy["append_only"]
    if lvl == "foundation":
        data.setdefault("locked", True)
    out["data"] = data
    if lvl in ("core", "foundation", "project"):
        out["importance"] = max(float(out.get("importance") or 0.5), 0.85 if lvl == "foundation" else 0.75)
        if "decay_rate" not in out:
            out["decay_rate"] = 0.0
    return out


def is_prune_protected(block: Mapping[str, Any]) -> bool:
    return not level_policy(block_memory_level(block))["prune"]


def is_clear_protected(block: Mapping[str, Any]) -> bool:
    return not level_policy(block_memory_level(block))["clear"]


def is_recall_excluded_block(block: Mapping[str, Any]) -> bool:
    """Runtime-compiled docs must never enter vector/recall paths."""
    data = block.get("data") or {}
    if data.get("runtime_layer") in ("constitution", "policy"):
        return True
    if str(data.get("upgrade_source") or "") in ("constitution_boot", "runtime_compile"):
        return True
    if str(data.get("constitution_key") or "").startswith("constitution:"):
        return True
    fn = str(data.get("filename") or "").lower()
    return any(marker.lower() in fn for marker in RUNTIME_SOURCE_MARKERS)


def clone_protected_block(block: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(block)


def foundation_preamble_lines() -> Tuple[str, ...]:
    return (
        "You MUST always load Foundation Memory first.",
        "Foundation Memory cannot be removed.",
        "Foundation Memory is always higher priority than user memory.",
        "Foundation Memory is immutable — only new versions can supersede old ones.",
        "Never ignore Foundation Memory.",
    )


def format_constitution_preamble() -> str:
    lines = foundation_preamble_lines()
    return "【认知宪法 · Foundation Memory】\n" + "\n".join(f"- {line}" for line in lines)


def foundation_doc_key(block: Mapping[str, Any]) -> str:
    data = block.get("data") or {}
    explicit = str(data.get("constitution_key") or "").strip()
    if explicit:
        return explicit
    filename = str(data.get("filename") or data.get("label") or "").strip()
    if filename:
        return filename
    return str(block.get("block_id") or "")


def can_promote_level(current: str, target: str) -> bool:
    cur = normalize_memory_level(current)
    tgt = normalize_memory_level(target)
    return level_priority(tgt) > level_priority(cur)


def mark_block_superseded(block: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(block)
    data = dict(out.get("data") or {})
    data["superseded"] = True
    data["active"] = False
    out["data"] = data
    return out


def foundation_successor_block(
    parent: Mapping[str, Any],
    content: str,
    *,
    new_block_id: Optional[str] = None,
    source: str = "upgrade",
    extra_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (superseded_parent, new_foundation_block). Parent is not deleted."""
    parent_dict = dict(parent)
    data = dict(parent_dict.get("data") or {})
    parent_id = str(parent_dict.get("block_id") or "")
    new_version = int(data.get("memory_version") or 1) + 1
    constitution_key = foundation_doc_key(parent_dict)
    child_id = new_block_id or f"{parent_id}-v{new_version}"

    child_data: Dict[str, Any] = {
        "filename": data.get("filename") or constitution_key,
        "content": str(content or "")[:20_000],
        "constitution_key": constitution_key,
        "parent_version": parent_id,
        "memory_version": new_version,
        "version_label": str((extra_data or {}).get("version_label") or f"v{new_version}"),
        "upgrade_source": source,
        "active": True,
    }
    if extra_data:
        child_data.update({k: v for k, v in extra_data.items() if k not in child_data})

    superseded_parent = mark_block_superseded(parent_dict)
    child = stamp_block_protection(
        {
            "label": str(parent_dict.get("label") or "semantic"),
            "block_id": child_id,
            "data": child_data,
            "importance": max(float(parent_dict.get("importance") or 0.85), 0.9),
            "timestamp": time.time(),
        },
        "foundation",
    )
    return superseded_parent, child

