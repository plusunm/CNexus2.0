"""Ed25519 signing for compiled Runtime bundles."""

from __future__ import annotations

from typing import Any, Dict

from .types import CompiledRuntime


def bundle_sign_payload(compiled: CompiledRuntime) -> Dict[str, Any]:
    return {
        "bundle_version": compiled.bundle_version,
        "compiled_at": compiled.compiled_at,
        "content_signature": compiled.content_signature,
    }


def attach_ed25519_signature(compiled: CompiledRuntime, identity_manager: Any) -> Dict[str, Any]:
    if identity_manager is None:
        return {"ok": False, "error": "identity_unavailable"}
    signed = identity_manager.sign_payload(bundle_sign_payload(compiled))
    return {
        "ok": True,
        "signature": signed.get("signature"),
        "pubkey": signed.get("pubkey"),
        "algorithm": signed.get("algorithm", "Ed25519"),
        "payload": signed.get("payload"),
    }


def merge_signature_into_bundle_dict(payload: Dict[str, Any], sig: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload)
    if sig.get("ok") and sig.get("signature"):
        out["bundle_signature"] = {
            "payload": sig.get("payload"),
            "signature": sig.get("signature"),
            "pubkey": sig.get("pubkey"),
            "algorithm": sig.get("algorithm", "Ed25519"),
        }
    return out


def verify_ed25519_bundle(raw_bundle: Dict[str, Any], identity_manager: Any) -> bool:
    envelope = raw_bundle.get("bundle_signature")
    if not isinstance(envelope, dict) or identity_manager is None:
        return False
    return bool(identity_manager.verify_payload(envelope, envelope.get("pubkey")))
