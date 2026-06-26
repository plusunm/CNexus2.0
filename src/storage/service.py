"""Storage service — Chunk truth + Descriptor contract + P4.5 transfer."""

from __future__ import annotations

import base64
from typing import Any, Dict, Iterable, List, Optional

try:
    from protocol.constants import ALLOWED_CHUNK_ENCODINGS
    from protocol.models import ChunkDescriptor, Manifest
except ImportError:
    from cnexus_protocol.constants import ALLOWED_CHUNK_ENCODINGS
    from cnexus_protocol.models import ChunkDescriptor, Manifest

from . import chunk_exchange_client
from .chunk_store import ChunkStore
from .chunk_verifier import ChunkVerifyError, verify_chunk_bytes
from .descriptor_store import DescriptorStore
from .manifest_store import ManifestStore


class StorageService:
    """
    Storage Layer facade.

    Manifest ≠ truth. Chunk = truth. Commit = ordering.
    ChunkDescriptor = network contract (NOT Manifest).
    Chunk is owned by Hash — not Manifest, not Peer.
    """

    def __init__(
        self,
        chunk_store: ChunkStore,
        manifest_store: ManifestStore,
        descriptor_store: Optional[DescriptorStore] = None,
    ):
        self.chunks = chunk_store
        self.manifests = manifest_store
        self.descriptors = descriptor_store

    def _record_descriptor(
        self,
        content: bytes,
        chunk_hash: str,
        *,
        created_by: str = "",
        verifier_peer_id: str = "",
        source_peer_id: str = "",
        descriptor_row: Optional[Dict[str, Any]] = None,
        encoding: str = "raw",
    ) -> Optional[ChunkDescriptor]:
        if self.descriptors is None:
            return None
        if descriptor_row:
            row = dict(descriptor_row)
            row["hash"] = chunk_hash
            row["size"] = len(content)
            desc = ChunkDescriptor.from_dict(row)
            if desc.encoding not in ALLOWED_CHUNK_ENCODINGS:
                raise ValueError(f"unsupported encoding: {desc.encoding}")
        else:
            desc = ChunkDescriptor.for_content(content, chunk_hash, created_by=created_by, encoding=encoding)
        return self.descriptors.save(
            desc,
            verifier_peer_id=verifier_peer_id,
            source_peer_id=source_peer_id,
        )

    def put_chunk(
        self,
        content: bytes,
        *,
        expected_hash: str = "",
        created_by: str = "",
        verifier_peer_id: str = "",
        source_peer_id: str = "",
        descriptor: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, Any], int]:
        try:
            chunk_hash = self.chunks.put(content, expected_hash=expected_hash)
            desc = self._record_descriptor(
                content,
                chunk_hash,
                created_by=created_by,
                verifier_peer_id=verifier_peer_id or created_by,
                source_peer_id=source_peer_id,
                descriptor_row=descriptor,
            )
        except ChunkVerifyError as exc:
            return {"ok": False, "error": "chunk_verify_failed", "detail": str(exc)}, 400
        except Exception as exc:
            return {"ok": False, "error": "chunk_put_failed", "detail": str(exc)}, 400
        payload: Dict[str, Any] = {
            "ok": True,
            "hash": chunk_hash,
            "chunk_hash": chunk_hash,
            "size": len(content),
            "verified": True,
            "encoding": (desc.encoding if desc else "raw"),
        }
        if desc:
            payload["descriptor"] = desc.to_dict()
        return payload, 200

    def chunk_state(self, chunk_hash: str) -> tuple[Dict[str, Any], int]:
        """P4.5-A — Chunk discovery / state alignment (no bytes)."""
        present = self.chunks.has(chunk_hash)
        verified = self.chunks.verify(chunk_hash) if present else False
        desc = self.descriptors.get(chunk_hash) if self.descriptors else None
        if present and desc is None:
            content = self.chunks.get(chunk_hash) or b""
            desc = ChunkDescriptor.for_content(content, chunk_hash)
        return {
            "ok": True,
            "exists": present,
            "hash": chunk_hash,
            "size": int(desc.size if desc else 0),
            "encoding": str(desc.encoding if desc else "raw"),
            "compression": desc.compression if desc else None,
            "verified": verified,
            "descriptor": desc.to_dict() if desc else None,
            "peers": list(desc.sources) if desc else [],
        }, 200

    def chunk_transfer_get(self, chunk_hash: str) -> tuple[Dict[str, Any], int]:
        """P4.5-B — Transfer chunk bytes (only after local verify)."""
        if not self.chunks.has(chunk_hash):
            return {"ok": False, "error": "chunk_not_found", "hash": chunk_hash}, 404
        if not self.chunks.verify(chunk_hash):
            return {"ok": False, "error": "chunk_invalid", "hash": chunk_hash}, 500
        content = self.chunks.get(chunk_hash) or b""
        desc = self.descriptors.get(chunk_hash) if self.descriptors else None
        if desc is None:
            desc = ChunkDescriptor.for_content(content, chunk_hash)
        return {
            "ok": True,
            "hash": chunk_hash,
            "size": len(content),
            "encoding": desc.encoding,
            "bytes": base64.b64encode(content).decode("ascii"),
            "descriptor": desc.to_dict(),
        }, 200

    def pull_chunk_from_peer(
        self,
        peer_host: str,
        chunk_hash: str,
        *,
        verifier_peer_id: str = "",
    ) -> Dict[str, Any]:
        """
        P4.5 explicit pull: request → verify(bytes→hash) → store.
        No auto-sync, replication, or gossip.
        """
        report: Dict[str, Any] = {"ok": False, "hash": chunk_hash, "peer_host": peer_host}
        if self.chunks.has(chunk_hash) and self.chunks.verify(chunk_hash):
            report.update({"ok": True, "skipped": True, "reason": "already_present"})
            return report
        try:
            state = chunk_exchange_client.fetch_chunk_state(peer_host, chunk_hash)
        except Exception as exc:
            report["error"] = str(exc)
            report["phase"] = "state"
            return report
        if not state.get("exists"):
            report["error"] = "remote_missing"
            return report
        remote_encoding = str(state.get("encoding") or "raw")
        if remote_encoding not in ALLOWED_CHUNK_ENCODINGS:
            report["error"] = f"unsupported_encoding:{remote_encoding}"
            return report
        try:
            remote = chunk_exchange_client.fetch_chunk(peer_host, chunk_hash)
        except Exception as exc:
            report["error"] = str(exc)
            report["phase"] = "transfer"
            return report
        content = chunk_exchange_client.decode_chunk_bytes(remote)
        expected = str(remote.get("hash") or chunk_hash)
        if not verify_chunk_bytes(content, expected):
            report["error"] = "verify_failed"
            return report
        remote_desc = remote.get("descriptor") if isinstance(remote.get("descriptor"), dict) else {}
        payload, status = self.put_chunk(
            content,
            expected_hash=expected,
            created_by=str(remote_desc.get("created_by") or ""),
            verifier_peer_id=verifier_peer_id,
            source_peer_id=peer_host,
            descriptor=remote_desc or None,
        )
        report.update(payload)
        report["pulled"] = status == 200
        return report

    def chunk_has(self, chunk_hash: str) -> tuple[Dict[str, Any], int]:
        present = self.chunks.has(chunk_hash)
        return {"ok": True, "chunk_hash": chunk_hash, "hash": chunk_hash, "present": present}, 200

    def chunk_verify(self, chunk_hash: str, *, content: Optional[bytes] = None) -> tuple[Dict[str, Any], int]:
        if content is not None:
            verified = self.chunks.verify(chunk_hash, content=content)
            return {
                "ok": verified,
                "chunk_hash": chunk_hash,
                "hash": chunk_hash,
                "present": True,
                "verified": verified,
                "source": "inline_bytes",
            }, 200 if verified else 400
        present = self.chunks.has(chunk_hash)
        if not present:
            return {"ok": False, "chunk_hash": chunk_hash, "hash": chunk_hash, "present": False, "verified": False}, 404
        verified = self.chunks.verify(chunk_hash)
        return {
            "ok": verified,
            "chunk_hash": chunk_hash,
            "hash": chunk_hash,
            "present": True,
            "verified": verified,
            "source": "local_store",
        }, 200 if verified else 400

    def verify_manifest_binding(
        self,
        *,
        root_hash: str = "",
        commit_id: str = "",
        manifest: Optional[Manifest] = None,
    ) -> tuple[Dict[str, Any], int]:
        resolved = manifest
        if resolved is None:
            if commit_id:
                resolved = self.manifests.get_by_commit(commit_id)
            elif root_hash:
                resolved = self.manifests.get(root_hash)
        if resolved is None:
            return {"ok": False, "error": "manifest_not_found"}, 404

        present: List[str] = []
        missing: List[str] = []
        invalid: List[str] = []
        for h in resolved.chunk_hashes():
            if not self.chunks.has(h):
                missing.append(h)
                continue
            if self.chunks.verify(h):
                present.append(h)
            else:
                invalid.append(h)

        complete = not missing and not invalid
        return {
            "ok": complete,
            "root_hash": resolved.root_hash,
            "chunk_count": len(resolved.chunk_hashes()),
            "present": present,
            "missing": missing,
            "invalid": invalid,
            "binding_complete": complete,
        }, 200

    def ingest_chunk_payloads(self, payloads: Iterable[Dict[str, Any]], *, created_by: str = "") -> Dict[str, Any]:
        stored: List[str] = []
        errors: List[Dict[str, str]] = []
        for row in payloads or []:
            if not isinstance(row, dict):
                continue
            raw = row.get("bytes") or row.get("content") or b""
            if isinstance(raw, str):
                raw = base64.b64decode(raw.encode("ascii"))
            expected = str(row.get("hash") or row.get("chunk_hash") or "")
            desc_row = row.get("descriptor") if isinstance(row.get("descriptor"), dict) else None
            try:
                payload, status = self.put_chunk(
                    raw,
                    expected_hash=expected,
                    created_by=created_by,
                    descriptor=desc_row,
                )
                if status == 200:
                    stored.append(str(payload.get("hash") or expected))
                else:
                    errors.append({"hash": expected, "error": str(payload.get("error") or "put_failed")})
            except Exception as exc:
                errors.append({"hash": expected, "error": str(exc)})
        return {"ok": not errors, "stored": stored, "errors": errors}

    def status(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "ok": True,
            "chunks": self.chunks.status(),
            "manifests": self.manifests.status(),
        }
        if self.descriptors is not None:
            payload["descriptors"] = self.descriptors.status()
        return payload
