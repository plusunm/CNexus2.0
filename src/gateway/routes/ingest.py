"""HTTP adapters for document ingest endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..http.responses import HttpRouteResponse
from ..services.ingest import DocumentIngestService, _policy_from_form_fields
from ..utils.multipart import iter_uploaded_files, parse_multipart, read_uploaded_file

JsonResponse = Tuple[Dict[str, Any], int]


class IngestRouteHandler:
    def __init__(self, service: DocumentIngestService):
        self._service = service

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path == "/api/ingest/document":
            payload, status = self.handle_api_ingest_document(http.rfile, http.headers)
            return HttpRouteResponse.json(payload, status)
        if path == "/api/ingest/documents":
            payload, status = self.handle_api_ingest_documents(http.rfile, http.headers)
            return HttpRouteResponse.json(payload, status)
        if path == "/api/ingest/documents/stage":
            payload, status = self.handle_api_stage_documents(http.rfile, http.headers)
            return HttpRouteResponse.json(payload, status)
        if path == "/v1/memory/capture":
            payload, status = self.handle_memory_capture(http._get_post_data())
            return HttpRouteResponse.json(payload, status)
        return None

    def handle_gateway_file_upload(self, rfile, headers) -> JsonResponse:
        form = parse_multipart(rfile, headers)
        if not form:
            return {"ok": False, "error": "expected multipart upload"}, 400
        raw, filename = read_uploaded_file(form)
        if raw is None:
            return {"ok": False, "error": "missing file"}, 400
        return self._service.stage_upload(filename or "upload.txt", raw, persist_blob=False)

    def handle_api_ingest_document(self, rfile, headers) -> JsonResponse:
        form = parse_multipart(rfile, headers)
        if not form:
            return {"ok": False, "error": "expected multipart upload"}, 400
        raw, filename = read_uploaded_file(form)
        if raw is None:
            return {"ok": False, "error": "missing file"}, 400
        policy = _policy_from_form_fields(form)
        layer = str(policy.get("layer") or "episodic")
        importance = float(policy.get("importance") or 0.7)
        label = None
        if "label" in form:
            label = str(form["label"].value or "").strip() or None
        return self._service.ingest_document(
            filename or "upload.txt",
            raw,
            layer=layer,
            importance=importance,
            label=label,
            policy=policy,
        )

    def handle_api_ingest_documents(self, rfile, headers) -> JsonResponse:
        form = parse_multipart(rfile, headers)
        if not form:
            return {"ok": False, "error": "expected multipart upload"}, 400
        uploads = iter_uploaded_files(form)
        if not uploads:
            return {"ok": False, "error": "missing files"}, 400
        policy = _policy_from_form_fields(form)
        layer = str(policy.get("layer") or "episodic")
        importance = float(policy.get("importance") or 0.7)
        return self._service.ingest_documents_batch(
            uploads,
            layer=layer,
            importance=importance,
            policy=policy,
        )

    def handle_api_stage_documents(self, rfile, headers) -> JsonResponse:
        form = parse_multipart(rfile, headers)
        if not form:
            return {"ok": False, "error": "expected multipart upload"}, 400
        uploads = iter_uploaded_files(form)
        if not uploads:
            return {"ok": False, "error": "missing files"}, 400
        return self._service.stage_documents_batch(uploads)

    def handle_file_process_intent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        file_id = str(payload.get("file_id") or "")
        policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
        return self._service.process_staged(file_id, policy)

    def handle_memory_capture(self, body: Dict[str, Any]) -> JsonResponse:
        content = str(body.get("content") or "")
        layer = str(body.get("layer") or "episodic")
        label = str(body.get("label") or "capture")
        try:
            importance = float(body.get("importance") or 0.6)
        except (TypeError, ValueError):
            importance = 0.6
        return self._service.capture_text(content, layer=layer, label=label, importance=importance), 200
