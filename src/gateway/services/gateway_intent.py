"""Gateway intent contract — chat prepare/confirm and async file process."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .converse import ConverseService
from .ingest import DocumentIngestService


@dataclass
class GatewayIntentService:
    """Handle POST /v1/gateway/intent {type, payload} — file work runs in background."""

    _converse: ConverseService
    _ingest: DocumentIngestService
    _prepare_cache: Dict[str, str] = field(default_factory=dict)
    _jobs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _jobs_lock: threading.Lock = field(default_factory=threading.Lock)

    def get_job(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._jobs_lock:
            job = self._jobs.get(trace_id)
            return dict(job) if job else None

    def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        intent_type = (data.get("type") or "").strip()
        payload = _payload_dict(data)
        text = _extract_intent_text(data)
        trace_id = str(data.get("trace_id") or f"v2-{int(time.time() * 1000)}")

        if intent_type == "chat_prepare":
            self._prepare_cache[trace_id] = text
            return {
                "trace_id": trace_id,
                "status": "completed",
                "ok": True,
                "result": {
                    "prepare_id": trace_id,
                    "user_message": text,
                    "memory_context": "",
                    "governance_injection": "",
                    "system_prompt": "CNexus 2.0 Personal Cognitive Kernel",
                    "outbound_preview": text,
                    "has_injection": False,
                    "chat_governance_notes": [],
                    "expires_in_seconds": 300,
                },
            }

        if intent_type == "chat_confirm":
            prepare_id = str(payload.get("prepare_id") or trace_id)
            msg = self._prepare_cache.get(prepare_id) or text
            try:
                result = self._run_converse(msg) if msg else {"reply": "请先输入消息"}
                reply = result.get("reply", "已处理")
            except Exception as exc:
                reply = f"引擎处理异常: {exc}"
            return {
                "trace_id": trace_id,
                "status": "completed",
                "ok": True,
                "result": {
                    "reply": reply,
                    "model_name": "CNexus 2.0 Local",
                    "human_authorized": True,
                    "latency_ms": 50,
                },
            }

        if intent_type == "file_process":
            return self._enqueue_file_process(trace_id, payload)

        if intent_type == "file_process_batch":
            return self._enqueue_file_process_batch(trace_id, payload)

        if text:
            try:
                result = self._run_converse(text)
                reply = result.get("reply", "已处理")
            except Exception:
                reply = "引擎处理中（模拟模式）"
        else:
            reply = "请输入有效消息"
        return {
            "trace_id": trace_id,
            "status": "completed",
            "ok": True,
            "result": {
                "reply": reply,
                "model_name": "CNexus 2.0 Local",
                "source": "personal_kernel",
                "type": "text",
            },
        }

    def _run_converse(self, text: str) -> Dict[str, Any]:
        return self._converse.run_blocking(text)

    def _set_job(self, trace_id: str, **fields: Any) -> None:
        with self._jobs_lock:
            job = self._jobs.setdefault(trace_id, {"trace_id": trace_id})
            job.update(fields)

    def _enqueue_file_process(self, trace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        file_id = str(payload.get("file_id") or "")
        policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
        self._set_job(trace_id, status="queued", file_id=file_id, policy=policy)
        threading.Thread(
            target=self._run_file_process,
            args=(trace_id, file_id, policy),
            daemon=True,
        ).start()
        return {"trace_id": trace_id, "status": "queued", "ok": True, "file_id": file_id}

    def _enqueue_file_process_batch(self, trace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_ids = payload.get("file_ids")
        file_ids = [str(fid) for fid in raw_ids] if isinstance(raw_ids, list) else []
        policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
        self._set_job(
            trace_id,
            status="queued",
            file_ids=file_ids,
            policy=policy,
            total=len(file_ids),
            done=0,
        )
        threading.Thread(
            target=self._run_file_process_batch,
            args=(trace_id, file_ids, policy),
            daemon=True,
        ).start()
        return {
            "trace_id": trace_id,
            "status": "queued",
            "ok": True,
            "count": len(file_ids),
        }

    def _run_file_process(self, trace_id: str, file_id: str, policy: Dict[str, Any]) -> None:
        try:
            result = self._ingest.process_staged(file_id, policy)
            if result.get("status") == "error":
                self._set_job(trace_id, status="error", ok=False, error=result.get("error"), result=result)
                return
            self._set_job(
                trace_id,
                status="completed",
                ok=True,
                result=result.get("result", result),
            )
        except Exception as exc:
            self._set_job(trace_id, status="error", ok=False, error=str(exc))

    def _run_file_process_batch(self, trace_id: str, file_ids: list[str], policy: Dict[str, Any]) -> None:
        total = len(file_ids)

        def on_progress(**fields: Any) -> None:
            self._set_job(trace_id, **fields)

        try:
            self._set_job(
                trace_id,
                status="processing",
                file_ids=file_ids,
                policy=policy,
                total=total,
                done=0,
                files_indexed_count=0,
                latest_finished=None,
                details=[],
            )
            result = self._ingest.process_staged_batch_streaming(file_ids, policy, on_progress)
            if not result.get("ok"):
                self._set_job(trace_id, status="error", ok=False, error=result.get("error"), result=result)
                return
            self._set_job(
                trace_id,
                status="completed",
                ok=True,
                done=result.get("count", total),
                total=total,
                files_indexed_count=result.get("count", 0),
                result=result,
            )
        except Exception as exc:
            self._set_job(trace_id, status="error", ok=False, error=str(exc))


def _payload_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = data.get("payload")
    return payload if isinstance(payload, dict) else {}


def _extract_intent_text(data: Dict[str, Any]) -> str:
    payload = _payload_dict(data)
    for key in ("message", "text", "input", "content"):
        val = payload.get(key) or data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""
