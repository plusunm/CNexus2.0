"""Document upload, staging, indexing, and memory capture."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..state import EngineStateManager
from ..utils.text import decode_upload_bytes, extract_keywords

FAST_TEXT_EXTENSIONS = frozenset({"txt", "md", "markdown"})


def fast_track_rank(filename: str) -> int:
    """0 = text fast path, 1 = heavier formats."""
    ext = os.path.splitext(str(filename or ""))[1].lstrip(".").lower()
    return 0 if ext in FAST_TEXT_EXTENSIONS else 1

GtbsRowFn = Callable[..., Dict[str, Any]]
AppendLogFn = Callable[..., None]
SchedulePersistFn = Callable[[], None]


@dataclass(frozen=True)
class IngestHooks:
    touch_activity: Callable[[], None]
    append_log: AppendLogFn
    gtbs_row: GtbsRowFn
    schedule_persist: SchedulePersistFn


class DocumentIngestService:
    """File staging + episodic memory indexing — no HTTP objects."""

    MAX_CONTENT_CHARS = 20_000
    MEMORY_SNIPPET_CHARS = 2_000
    PREVIEW_CHARS = 400

    def __init__(
        self,
        state: EngineStateManager,
        hooks: IngestHooks,
        *,
        assets_dir: str,
    ):
        self._state = state
        self._hooks = hooks
        self._assets_dir = assets_dir
        self._file_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    def stage_upload(self, filename: str, raw: bytes, *, persist_blob: bool = True) -> Tuple[Dict[str, Any], int]:
        """Stage bytes for gateway two-step upload (file/upload + file_process intent)."""
        if not raw:
            return {"ok": False, "error": "empty file"}, 400
        self._hooks.touch_activity()
        file_id = f"file-{int(time.time() * 1000)}"
        asset_path = self._persist_asset_blob(file_id, filename, raw) if persist_blob else ""
        with self._cache_lock:
            self._file_cache[file_id] = {
                "filename": filename,
                "raw": raw,
                "content": decode_upload_bytes(raw) if persist_blob else "",
                "asset_path": asset_path,
                "size": len(raw),
            }
        ext = os.path.splitext(filename)[1].lstrip(".") or "txt"
        return {
            "file_id": file_id,
            "filename": filename,
            "file_type": ext,
            "trace_id": file_id,
            "ok": True,
        }, 200

    def stage_documents_batch(
        self,
        files: List[Tuple[str, bytes]],
    ) -> Tuple[Dict[str, Any], int]:
        """Fast receive — memory cache only, no per-file disk writes."""
        if not files:
            return {"ok": False, "error": "no files"}, 400
        self._hooks.touch_activity()
        batch_id = f"batch-{int(time.time() * 1000)}"
        trace_id = f"v2-trace-{batch_id}"
        file_ids: List[str] = []
        errors: List[Dict[str, Any]] = []

        with self._cache_lock:
            for idx, (filename, raw) in enumerate(files):
                if not raw:
                    errors.append({"filename": filename, "error": "empty file"})
                    continue
                file_id = f"file-{batch_id}-{idx}"
                self._file_cache[file_id] = {
                    "filename": filename,
                    "raw": raw,
                    "content": "",
                    "asset_path": "",
                    "size": len(raw),
                }
                file_ids.append(file_id)

        if not file_ids:
            return {"ok": False, "error": "no valid files", "errors": errors}, 400

        return {
            "ok": True,
            "batch_id": batch_id,
            "trace_id": trace_id,
            "file_ids": file_ids,
            "count": len(file_ids),
            "status": "received",
            "errors": errors,
        }, 200

    def process_staged_batch(
        self,
        file_ids: List[str],
        policy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Index many staged uploads in one memory transaction."""
        policy = policy or {}
        layer = str(policy.get("layer") or "episodic")
        importance = float(policy.get("importance") or 0.7)
        batch_id = f"batch-{int(time.time() * 1000)}"
        trace_id = f"v2-trace-{batch_id}"
        base_ts = time.time()
        pending_blocks: List[Dict[str, Any]] = []
        indexed: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        with self._cache_lock:
            for idx, file_id in enumerate(file_ids):
                entry = dict(self._file_cache.get(file_id) or {})
                if not entry:
                    errors.append({"file_id": file_id, "error": "unknown file_id"})
                    continue
                filename = str(entry.get("filename") or "document")
                raw = entry.get("raw")
                if raw is not None and not entry.get("content"):
                    content = decode_upload_bytes(raw)
                    entry["content"] = content
                    self._file_cache[file_id] = entry
                else:
                    content = str(entry.get("content") or "")
                snippet = content[: self.MEMORY_SNIPPET_CHARS]
                keywords = extract_keywords(content, 6)
                mem_id = f"mem-{batch_id}-{idx}"
                pending_blocks.append(
                    {
                        "label": layer,
                        "block_id": mem_id,
                        "data": {"filename": filename, "content": snippet, "keywords": keywords},
                        "importance": importance,
                        "timestamp": base_ts + idx * 0.001,
                    }
                )
                preview = content[: self.PREVIEW_CHARS] if content else filename
                indexed.append(
                    {
                        "file_id": file_id,
                        "memory_id": mem_id,
                        "filename": filename,
                        "status": "indexed",
                        "preview": preview,
                        "keywords": keywords[:8],
                        "char_count": len(content),
                    }
                )

        if not pending_blocks:
            return {"ok": False, "status": "error", "error": "no staged files", "errors": errors}

        def apply(store) -> None:
            for block in pending_blocks:
                store.add(block)

        self._state.mutate_memory_store(apply)
        self._state.extend_gtbs_events(
            [
                self._hooks.gtbs_row(
                    "commit",
                    batch_id,
                    trace_id,
                    "capture",
                    "batch_ingest",
                    extra={"count": len(indexed), "layer": layer, "source": "file_process_batch"},
                ),
            ]
        )
        self._hooks.append_log(
            f"批量文档索引 · {len(indexed)} 个文件",
            category="capture",
            trace_id=trace_id,
        )
        self._hooks.schedule_persist()

        return {
            "ok": True,
            "batch_id": batch_id,
            "trace_id": trace_id,
            "status": "indexed",
            "count": len(indexed),
            "indexed": indexed,
            "errors": errors,
        }

    def process_staged_batch_streaming(
        self,
        file_ids: List[str],
        policy: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Index staged files one-by-one — text types first, with per-file progress."""
        policy = policy or {}
        ordered: List[Tuple[str, str]] = []
        with self._cache_lock:
            for file_id in file_ids:
                entry = self._file_cache.get(file_id) or {}
                filename = str(entry.get("filename") or file_id)
                ordered.append((file_id, filename))
        ordered.sort(key=lambda row: (fast_track_rank(row[1]), row[1].lower()))

        total = len(ordered)
        indexed: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        details: List[Dict[str, Any]] = []

        def emit(**fields: Any) -> None:
            if on_progress:
                on_progress(**fields)

        emit(
            status="processing",
            done=0,
            total=total,
            files_indexed_count=0,
            latest_finished=None,
            details=[],
        )

        for i, (file_id, filename) in enumerate(ordered):
            row = self.process_staged(file_id, policy)
            ok = bool(row.get("ok")) and row.get("status") != "error"
            inner = row.get("result") if isinstance(row.get("result"), dict) else {}
            if ok:
                item = {
                    "file_id": file_id,
                    "memory_id": (inner.get("memory_ids") or [None])[0],
                    "filename": inner.get("filename") or filename,
                    "status": "indexed",
                    "preview": inner.get("preview") or filename,
                    "keywords": inner.get("keywords") or [],
                    "char_count": len(str(inner.get("preview") or "")),
                }
                indexed.append(item)
                details.append({"file_id": file_id, "filename": item["filename"], "status": "indexed"})
                latest = item["filename"]
            else:
                err = {
                    "file_id": file_id,
                    "filename": filename,
                    "error": row.get("error") or "index failed",
                }
                errors.append(err)
                details.append({"file_id": file_id, "filename": filename, "status": "error"})
                latest = None

            emit(
                status="processing",
                done=i + 1,
                total=total,
                files_indexed_count=len(indexed),
                latest_finished=latest,
                details=list(details),
            )

        if not indexed:
            return {"ok": False, "status": "error", "error": "no staged files", "errors": errors}

        return {
            "ok": True,
            "status": "indexed",
            "count": len(indexed),
            "indexed": indexed,
            "errors": errors,
        }

    def process_staged(self, file_id: str, policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Index a staged upload into memory (gateway file_process intent)."""
        policy = policy or {}
        with self._cache_lock:
            entry = dict(self._file_cache.get(file_id) or {})
        if not entry:
            return {
                "trace_id": file_id,
                "status": "error",
                "ok": False,
                "error": f"unknown file_id: {file_id}",
            }
        raw = entry.get("raw")
        if raw is not None and not entry.get("content"):
            entry["content"] = decode_upload_bytes(raw)
        layer = str(policy.get("layer") or "episodic")
        importance = float(policy.get("importance") or 0.7)
        result = self._index_document(
            filename=str(entry.get("filename") or "document"),
            content=str(entry.get("content") or ""),
            layer=layer,
            importance=importance,
            file_id=file_id,
            source="gateway_file_process",
        )
        return {
            "trace_id": result["trace_id"],
            "status": "completed",
            "ok": True,
            "result": result,
        }

    def ingest_document(
        self,
        filename: str,
        raw: bytes,
        *,
        layer: str = "episodic",
        importance: float = 0.7,
        label: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """One-shot Personal API: upload + index."""
        if not raw:
            return {"ok": False, "error": "empty file"}, 400
        self._hooks.touch_activity()
        content = decode_upload_bytes(raw)
        file_id = f"file-{int(time.time() * 1000)}"
        self._persist_asset_blob(file_id, filename, raw)
        indexed = self._index_document(
            filename=label or filename,
            content=content,
            layer=layer,
            importance=importance,
            file_id=file_id,
            source="api_ingest_document",
        )
        return {
            "ok": True,
            "file_id": file_id,
            "memory_id": indexed["memory_ids"][0],
            "status": indexed["status"],
            "filename": indexed["filename"],
            "preview": indexed["preview"],
            "keywords": indexed["keywords"],
            "char_count": len(content),
        }, 200

    def ingest_documents_batch(
        self,
        files: List[Tuple[str, bytes]],
        *,
        layer: str = "episodic",
        importance: float = 0.7,
    ) -> Tuple[Dict[str, Any], int]:
        """Bulk one-shot ingest — single memory lock, no per-file blobs or keyword blocks."""
        if not files:
            return {"ok": False, "error": "no files"}, 400

        self._hooks.touch_activity()
        batch_id = f"batch-{int(time.time() * 1000)}"
        trace_id = f"v2-trace-{batch_id}"
        base_ts = time.time()
        pending_blocks: List[Dict[str, Any]] = []
        indexed: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for idx, (filename, raw) in enumerate(files):
            if not raw:
                errors.append({"filename": filename, "error": "empty file"})
                continue
            content = decode_upload_bytes(raw)
            snippet = content[: self.MEMORY_SNIPPET_CHARS]
            keywords = extract_keywords(content, 6)
            mem_id = f"mem-{batch_id}-{idx}"
            pending_blocks.append(
                {
                    "label": layer,
                    "block_id": mem_id,
                    "data": {"filename": filename, "content": snippet, "keywords": keywords},
                    "importance": importance,
                    "timestamp": base_ts + idx * 0.001,
                }
            )
            preview = content[: self.PREVIEW_CHARS] if content else filename
            indexed.append(
                {
                    "file_id": f"file-{batch_id}-{idx}",
                    "memory_id": mem_id,
                    "filename": filename,
                    "status": "indexed",
                    "preview": preview,
                    "keywords": keywords[:8],
                    "char_count": len(content),
                }
            )

        if not pending_blocks:
            return {"ok": False, "error": "no valid files", "errors": errors}, 400

        def apply(store) -> None:
            for block in pending_blocks:
                store.add(block)

        self._state.mutate_memory_store(apply)
        self._state.extend_gtbs_events(
            [
                self._hooks.gtbs_row(
                    "commit",
                    batch_id,
                    trace_id,
                    "capture",
                    "batch_ingest",
                    extra={"count": len(indexed), "layer": layer, "source": "api_ingest_documents"},
                ),
            ]
        )
        self._hooks.append_log(
            f"批量文档索引 · {len(indexed)} 个文件",
            category="capture",
            trace_id=trace_id,
        )
        self._hooks.schedule_persist()

        return {
            "ok": True,
            "batch_id": batch_id,
            "status": "indexed",
            "count": len(indexed),
            "indexed": indexed,
            "errors": errors,
        }, 200

    def capture_text(
        self,
        content: str,
        *,
        layer: str = "episodic",
        label: str = "capture",
        importance: float = 0.6,
    ) -> Dict[str, Any]:
        """Direct text capture (/v1/memory/capture)."""
        self._hooks.touch_activity()
        text = (content or "").strip()
        mem_id = f"mem-{int(time.time() * 1000)}"
        if text:
            self._write_memory_blocks(
                mem_id=mem_id,
                filename=label,
                content=text[: self.MEMORY_SNIPPET_CHARS],
                layer=layer,
                importance=importance,
                keyword_limit=6,
            )
            self._hooks.schedule_persist()
        return {"memory_id": mem_id, "status": "stored", "ok": True}

    def _index_document(
        self,
        *,
        filename: str,
        content: str,
        layer: str,
        importance: float,
        file_id: str,
        source: str,
    ) -> Dict[str, Any]:
        snippet = content[: self.MEMORY_SNIPPET_CHARS]
        keywords = extract_keywords(content, 6)
        mem_id = f"mem-{int(time.time() * 1000)}"
        trace_id = f"v2-trace-file-{int(time.time() * 1000)}"

        self._write_memory_blocks(
            mem_id=mem_id,
            filename=filename,
            content=snippet,
            layer=layer,
            importance=importance,
            keyword_limit=6,
        )

        upload_rows = [
            self._hooks.gtbs_row("proposal", f"{file_id}-upload", trace_id, "file_upload", "gateway_file_upload"),
            self._hooks.gtbs_row(
                "commit",
                f"{file_id}-index",
                trace_id,
                "capture",
                "file_process",
                extra={"target_stores": [layer], "filename": filename, "source": source},
            ),
        ]
        self._state.extend_gtbs_events(upload_rows)
        self._hooks.append_log(f"文档索引 · {filename}", category="capture", trace_id=trace_id)
        self._hooks.append_log(f"导入流注入记忆层 · {filename}", category="embed", trace_id=trace_id)
        self._hooks.schedule_persist()

        preview = content[: self.PREVIEW_CHARS] if content else filename
        return {
            "file_id": file_id,
            "status": "indexed",
            "filename": filename,
            "chunk_count": 1,
            "memory_ids": [mem_id],
            "summary": preview[:120],
            "keywords": keywords[:8],
            "preview": preview,
            "trace_id": trace_id,
        }

    def _write_memory_blocks(
        self,
        *,
        mem_id: str,
        filename: str,
        content: str,
        layer: str,
        importance: float,
        keyword_limit: int,
    ) -> List[str]:
        keywords = extract_keywords(content, keyword_limit)

        def apply(store) -> List[str]:
            store.add({
                "label": layer,
                "block_id": mem_id,
                "data": {"filename": filename, "content": content, "keywords": keywords},
                "importance": importance,
                "timestamp": time.time(),
            })
            for kw in keywords[:4]:
                store.add({
                    "label": layer,
                    "block_id": f"kw-{mem_id}-{kw}",
                    "data": {"content": kw, "filename": filename, "keywords": [kw]},
                    "importance": 0.45,
                    "timestamp": time.time(),
                })
            return keywords

        return self._state.mutate_memory_store(apply)

    def _persist_asset_blob(self, file_id: str, filename: str, raw: bytes) -> str:
        os.makedirs(self._assets_dir, exist_ok=True)
        ext = os.path.splitext(filename)[1]
        if not ext:
            ext = ".bin"
        safe_name = f"{file_id}{ext}"
        path = os.path.join(self._assets_dir, safe_name)
        with open(path, "wb") as handle:
            handle.write(raw)
        return path

    def gateway_upload_response(self, payload: Dict[str, Any], status: int) -> Dict[str, Any]:
        """Shadow /v1/gateway/file/upload — same payload, explicit ok flag."""
        return payload

    def gateway_process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Return shape consumed by gateway intent executor."""
        if result.get("status") == "error":
            return result
        return result
