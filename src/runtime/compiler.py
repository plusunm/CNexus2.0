"""Constitution Compiler — markdown sources → constitution.bin (signed JSON bundle)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Tuple

from .types import CompiledRuntime, RuntimeDocument

TEXT_EXTENSIONS = frozenset({".md", ".markdown", ".txt"})


def runtime_source_roots(app_root: str) -> Tuple[str, str]:
    base = os.path.join(app_root, "runtime")
    return (
        os.path.join(base, "constitution"),
        os.path.join(base, "policy"),
    )


def compiled_bundle_path(data_dir: str) -> str:
    return os.path.join(data_dir, "constitution.bin")


def _doc_id(layer: str, rel_path: str) -> str:
    safe = rel_path.replace("\\", "/").replace(" ", "_")
    return f"{layer}:{safe}"


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scan_layer(layer: str, root: str) -> List[RuntimeDocument]:
    docs: List[RuntimeDocument] = []
    if not root or not os.path.isdir(root):
        return docs
    for dirpath, _dirs, names in os.walk(root):
        for name in sorted(names):
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTENSIONS:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if rel.lower() == "readme.md":
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if not content.strip():
                continue
            docs.append(
                RuntimeDocument(
                    doc_id=_doc_id(layer, rel),
                    title=os.path.splitext(name)[0],
                    content=content.strip(),
                    layer=layer,
                    version="1.0.0",
                    source_path=rel,
                    content_hash=_hash_content(content),
                )
            )
    return docs


def compile_runtime_sources(app_root: str) -> CompiledRuntime:
    constitution_dir, policy_dir = runtime_source_roots(app_root)
    constitution = _scan_layer("constitution", constitution_dir)
    policy = _scan_layer("policy", policy_dir)
    compiled = CompiledRuntime(
        bundle_version="1",
        compiled_at=time.time(),
        content_signature="",
        constitution=constitution,
        policy=policy,
    )
    compiled.content_signature = compute_bundle_signature(compiled)
    return compiled


def compute_bundle_signature(compiled: CompiledRuntime) -> str:
    payload_docs = list(compiled.constitution) + list(compiled.policy)
    signature_material = "|".join(f"{d.doc_id}:{d.content_hash}" for d in payload_docs)
    return _hash_content(signature_material) if signature_material else ""


def verify_compiled_bundle(compiled: CompiledRuntime) -> bool:
    if not compiled.content_signature:
        return False
    for doc in list(compiled.constitution) + list(compiled.policy):
        if doc.content_hash != _hash_content(doc.content):
            return False
    return compiled.content_signature == compute_bundle_signature(compiled)


def write_compiled_bundle(compiled: CompiledRuntime, data_dir: str, *, identity_manager: Any = None) -> str:
    path = compiled_bundle_path(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    payload = compiled.to_dict()
    if identity_manager is not None:
        from .signing import attach_ed25519_signature, merge_signature_into_bundle_dict

        sig = attach_ed25519_signature(compiled, identity_manager)
        payload = merge_signature_into_bundle_dict(payload, sig)
        compiled.bundle_signature = payload.get("bundle_signature")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def read_compiled_bundle(data_dir: str, *, verify: bool = True) -> CompiledRuntime | None:
    path = compiled_bundle_path(data_dir)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        return None
    compiled = CompiledRuntime.from_dict(raw)
    if verify and not verify_compiled_bundle(compiled):
        return None
    return compiled


def read_compiled_bundle_raw(data_dir: str) -> Dict[str, Any] | None:
    path = compiled_bundle_path(data_dir)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return raw if isinstance(raw, dict) else None


def bundle_is_tampered(data_dir: str) -> bool:
    path = compiled_bundle_path(data_dir)
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        return True
    compiled = CompiledRuntime.from_dict(raw)
    return not verify_compiled_bundle(compiled)


def sources_newer_than_bundle(app_root: str, data_dir: str) -> bool:
    path = compiled_bundle_path(data_dir)
    if not os.path.isfile(path):
        return True
    bundle_mtime = os.path.getmtime(path)
    for root in runtime_source_roots(app_root):
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, names in os.walk(root):
            for name in names:
                ext = os.path.splitext(name)[1].lower()
                if ext not in TEXT_EXTENSIONS:
                    continue
                if os.path.getmtime(os.path.join(dirpath, name)) > bundle_mtime:
                    return True
    return False


def compile_if_needed(
    app_root: str,
    data_dir: str,
    *,
    force: bool = False,
    identity_manager: Any = None,
) -> Dict[str, object]:
    tampered = bundle_is_tampered(data_dir)
    if force or tampered or sources_newer_than_bundle(app_root, data_dir):
        compiled = compile_runtime_sources(app_root)
        path = write_compiled_bundle(compiled, data_dir, identity_manager=identity_manager)
        ed25519_ok = bool((compiled.bundle_signature or {}).get("signature")) if compiled.bundle_signature else False
        return {
            "recompiled": True,
            "path": path,
            "compiled": compiled,
            "signature_verified": True,
            "ed25519_signed": ed25519_ok,
            "tampered_replaced": tampered,
        }
    compiled = read_compiled_bundle(data_dir, verify=True)
    if compiled is None:
        compiled = compile_runtime_sources(app_root)
        path = write_compiled_bundle(compiled, data_dir, identity_manager=identity_manager)
        ed25519_ok = bool((compiled.bundle_signature or {}).get("signature")) if compiled.bundle_signature else False
        return {
            "recompiled": True,
            "path": path,
            "compiled": compiled,
            "signature_verified": True,
            "ed25519_signed": ed25519_ok,
            "tampered_replaced": True,
        }
    raw = read_compiled_bundle_raw(data_dir) or {}
    from .signing import verify_ed25519_bundle

    ed25519_ok = verify_ed25519_bundle(raw, identity_manager) if identity_manager else bool(raw.get("bundle_signature"))
    return {
        "recompiled": False,
        "path": compiled_bundle_path(data_dir),
        "compiled": compiled,
        "signature_verified": verify_compiled_bundle(compiled),
        "ed25519_signed": ed25519_ok,
        "tampered_replaced": False,
    }
