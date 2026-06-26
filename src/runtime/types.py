"""Runtime layer types — Constitution & Policy are not Memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BootPhase(str, Enum):
    BOOT = "boot"
    CONSTITUTION = "constitution"
    POLICY = "policy"
    FOUNDATION = "foundation"
    PROJECT = "project"
    TIMELINE = "timeline"
    WORKFLOW = "workflow"
    AGENT = "agent"
    CONVERSATION_READY = "conversation_ready"


@dataclass(frozen=True)
class RuntimeDocument:
    doc_id: str
    title: str
    content: str
    layer: str  # "constitution" | "policy"
    version: str = "1.0.0"
    parent_version: Optional[str] = None
    source_path: str = ""
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "layer": self.layer,
            "version": self.version,
            "parent_version": self.parent_version,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "RuntimeDocument":
        return cls(
            doc_id=str(raw.get("doc_id") or ""),
            title=str(raw.get("title") or ""),
            content=str(raw.get("content") or ""),
            layer=str(raw.get("layer") or "constitution"),
            version=str(raw.get("version") or "1.0.0"),
            parent_version=raw.get("parent_version"),
            source_path=str(raw.get("source_path") or ""),
            content_hash=str(raw.get("content_hash") or ""),
        )


@dataclass
class CompiledRuntime:
    """Compiled constitution.bin payload — loaded at BOOT, never vector-indexed."""

    bundle_version: str = "1"
    compiled_at: float = 0.0
    content_signature: str = ""
    bundle_signature: Optional[Dict[str, Any]] = None
    constitution: List[RuntimeDocument] = field(default_factory=list)
    policy: List[RuntimeDocument] = field(default_factory=list)
    boot_phase: BootPhase = BootPhase.CONVERSATION_READY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_version": self.bundle_version,
            "compiled_at": self.compiled_at,
            "content_signature": self.content_signature,
            "boot_phase": self.boot_phase.value,
            "constitution": [doc.to_dict() for doc in self.constitution],
            "policy": [doc.to_dict() for doc in self.policy],
            "bundle_signature": self.bundle_signature,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "CompiledRuntime":
        phase_raw = str(raw.get("boot_phase") or BootPhase.CONVERSATION_READY.value)
        try:
            phase = BootPhase(phase_raw)
        except ValueError:
            phase = BootPhase.CONVERSATION_READY
        return cls(
            bundle_version=str(raw.get("bundle_version") or "1"),
            compiled_at=float(raw.get("compiled_at") or 0),
            content_signature=str(raw.get("content_signature") or ""),
            bundle_signature=raw.get("bundle_signature") if isinstance(raw.get("bundle_signature"), dict) else None,
            constitution=[RuntimeDocument.from_dict(d) for d in raw.get("constitution") or []],
            policy=[RuntimeDocument.from_dict(d) for d in raw.get("policy") or []],
            boot_phase=phase,
        )

    def status_dict(self) -> Dict[str, Any]:
        return {
            "boot_phase": self.boot_phase.value,
            "bundle_version": self.bundle_version,
            "compiled_at": self.compiled_at,
            "content_signature": self.content_signature[:16] + "…" if self.content_signature else "",
            "ed25519_signed": bool(self.bundle_signature),
            "signer_pubkey": (
                str((self.bundle_signature or {}).get("pubkey") or "")[:16] + "…"
                if (self.bundle_signature or {}).get("pubkey")
                else ""
            ),
            "constitution_docs": len(self.constitution),
            "policy_docs": len(self.policy),
            "layers": ["constitution", "policy", "foundation", "project", "conversation"],
        }
