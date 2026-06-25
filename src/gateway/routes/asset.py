"""Cognitive asset search, upload, ingest, and P2P blob routes."""

from __future__ import annotations

import base64
import json
from typing import Any, Optional
from urllib.parse import parse_qs

from ..http.auth_gate import AuthGate
from ..http.responses import HttpRouteResponse
from ..routes.ingest import IngestRouteHandler
from ..services.asset_gateway import AssetGatewayService
from ..utils.multipart import parse_multipart


class AssetRouteHandler:
    """Asset CRUD/search/upload — returns None when path is not handled."""

    def __init__(self, assets: AssetGatewayService, ingest: IngestRouteHandler, auth: AuthGate):
        self._assets = assets
        self._ingest = ingest
        self._auth = auth

    def handle_get(self, path: str, query: Optional[str], headers: Any) -> Optional[HttpRouteResponse]:
        qs = parse_qs(query or "")

        if path == "/api/asset/search":
            search_query = (qs.get("q", [""])[0] or "").strip()
            kind = (qs.get("kind", [""])[0] or "").strip() or None
            scope = (qs.get("scope", ["local"])[0] or "local").strip()
            try:
                limit = int(qs.get("limit", ["20"])[0] or "20")
            except ValueError:
                limit = 20
            payload, status = self._assets.search(search_query, kind=kind, limit=limit, scope=scope)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/search/semantic":
            search_query = (qs.get("q", [""])[0] or "").strip()
            kind = (qs.get("kind", [""])[0] or "").strip() or None
            scope = (qs.get("scope", ["local"])[0] or "local").strip()
            try:
                limit = int(qs.get("limit", ["10"])[0] or "10")
            except ValueError:
                limit = 10
            payload, status = self._assets.search_semantic(search_query, kind=kind, limit=limit, scope=scope)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/push/queue":
            process_flag = (qs.get("process", ["0"])[0] or "0").lower() in ("1", "true", "yes")
            try:
                limit = int(qs.get("limit", ["20"])[0] or "20")
            except ValueError:
                limit = 20
            payload, status = self._assets.push_queue(process=process_flag, limit=limit)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/reindex":
            payload, status = self._assets.reindex()
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/list":
            kind = (qs.get("kind", [""])[0] or "").strip() or None
            try:
                limit = int(qs.get("limit", ["50"])[0] or "50")
            except ValueError:
                limit = 50
            payload, status = self._assets.list_assets(kind=kind, limit=limit)
            return HttpRouteResponse.json(payload, status)

        if not path.startswith("/api/asset/"):
            return None

        asset_id = path[len("/api/asset/") :].strip("/")
        if not asset_id:
            return HttpRouteResponse.json({"ok": False, "error": "missing_asset_id"}, 400)

        raw_mode = (qs.get("raw", ["0"])[0] or "0").lower() in ("1", "true", "yes")
        include_content = (qs.get("content", ["0"])[0] or "0").lower() in ("1", "true", "yes")
        if include_content or raw_mode:
            denied = self._auth.check(
                path,
                headers,
                {"asset_id": asset_id, "content": 1 if include_content else 0, "raw": 1 if raw_mode else 0},
                method="GET",
            )
            if denied is not None:
                err, status = denied
                return HttpRouteResponse.json(err, status)

        if raw_mode:
            proc = self._assets.get_processor()
            if proc is None:
                return HttpRouteResponse.json({"ok": False, "error": "asset_processor_unavailable"}, 503)
            blob, meta, status = proc.read_raw(asset_id)
            if blob is None or meta is None:
                return HttpRouteResponse.json({"ok": False, "error": "asset_not_found"}, status)
            kind = meta.get("type") or "code"
            filename = str(meta.get("filename") or asset_id)
            if kind == "code":
                return HttpRouteResponse.bytes(blob, "text/plain; charset=utf-8", 200, filename=filename)
            mime = "image/jpeg"
            lower = filename.lower()
            if lower.endswith(".png"):
                mime = "image/png"
            elif lower.endswith(".gif"):
                mime = "image/gif"
            elif lower.endswith(".webp"):
                mime = "image/webp"
            return HttpRouteResponse.bytes(blob, mime, 200, filename=filename)

        payload, status = self._assets.get_asset(asset_id, include_content=include_content)
        return HttpRouteResponse.json(payload, status)

    def handle_post(self, path: str, http: Any) -> Optional[HttpRouteResponse]:
        if path == "/v1/gateway/file/upload":
            payload, status = self._ingest.handle_gateway_file_upload(http.rfile, http.headers)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/ingest/image":
            data = _read_json_body(http)
            return HttpRouteResponse.json(self._assets.ingest_image(data))

        if path == "/api/ingest/code":
            data = _read_json_body(http)
            return HttpRouteResponse.json(self._assets.ingest_code(data))

        if path == "/api/upload/code":
            return HttpRouteResponse.json(self._assets.upload_code(http._get_post_data()))

        if path == "/api/upload/image":
            ctype = http.headers.get("Content-Type", "")
            if "multipart/form-data" in ctype:
                form = parse_multipart(http)
                if not form:
                    return HttpRouteResponse.json({"ok": False, "error": "expected_multipart"}, 400)
                file_item = form["image"] if "image" in form else (form["file"] if "file" in form else None)
                if file_item is None or not getattr(file_item, "file", None):
                    return HttpRouteResponse.json({"ok": False, "error": "missing_image"}, 400)
                binary = file_item.file.read()
                filename = getattr(file_item, "filename", None) or "image.jpg"
                project_flag = False
                if "project" in form:
                    project_flag = str(form["project"].value or "").lower() in ("1", "true", "yes")
                body = self._assets.upload_image({"project": project_flag}, binary=binary, filename=filename)
                return HttpRouteResponse.json(body)
            return HttpRouteResponse.json(self._assets.upload_image(http._get_post_data()))

        if path == "/api/asset/receive":
            payload, status = self._assets.receive(http._get_post_data(), http.headers)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/pull":
            data = http._get_post_data()
            asset_id = str(data.get("asset_id") or data.get("id") or "")
            source_peer = str(data.get("source_peer") or data.get("peer_pubkey") or "")
            peer_host = str(data.get("peer_host") or data.get("host") or "")
            payload, status = self._assets.pull(asset_id, source_peer=source_peer, peer_host=peer_host)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/push":
            data = http._get_post_data()
            asset_id = str(data.get("asset_id") or data.get("id") or "")
            payload, status = self._assets.push(asset_id)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/push/queue":
            data = http._get_post_data()
            process_flag = bool(data.get("process"))
            try:
                limit = int(data.get("limit") or 20)
            except (TypeError, ValueError):
                limit = 20
            payload, status = self._assets.push_queue(process=process_flag, limit=limit)
            return HttpRouteResponse.json(payload, status)

        if path == "/api/asset/search/semantic":
            data = http._get_post_data()
            search_query = str(data.get("q") or data.get("query") or "").strip()
            kind = str(data.get("kind") or "").strip() or None
            scope = str(data.get("scope") or "local").strip()
            try:
                limit = int(data.get("limit") or 10)
            except (TypeError, ValueError):
                limit = 10
            image_bytes = None
            image_b64 = data.get("image_base64") or data.get("image") or ""
            raw_str = str(image_b64 or "").strip()
            if "," in raw_str:
                raw_str = raw_str.split(",", 1)[1]
            if raw_str:
                try:
                    image_bytes = base64.b64decode(raw_str)
                except Exception:
                    return HttpRouteResponse.json({"ok": False, "error": "invalid_image_base64"}, 400)
            payload, status = self._assets.search_semantic(
                search_query,
                kind=kind,
                limit=limit,
                image_bytes=image_bytes,
                scope=scope,
            )
            return HttpRouteResponse.json(payload, status)

        return None


def _read_json_body(http: Any) -> dict:
    length = int(http.headers.get("Content-Length", 0))
    body = http.rfile.read(length) if length > 0 else b"{}"
    try:
        return json.loads(body) if body else {}
    except Exception:
        return {}
