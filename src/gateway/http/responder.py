"""Shared HTTP response helpers for stdlib BaseHTTPRequestHandler adapters."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler
from typing import Any, Iterator, Optional, Union


class HttpResponderMixin(BaseHTTPRequestHandler):
    """JSON / SSE / bytes / static file helpers mixed into route handlers."""

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, data: Any, st: int = 200) -> None:
        self.send_response(st)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-CNexus-Signature, X-CNexus-Pubkey, X-CNexus-Timestamp, X-CNexus-Nonce",
        )
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, data: bytes, content_type: str, st: int = 200, filename: str = "") -> None:
        self.send_response(st)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        if filename:
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _sse(self, generator: Iterator[Union[str, bytes]], st: int = 200) -> None:
        self.send_response(st)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-CNexus-Signature, X-CNexus-Pubkey, X-CNexus-Timestamp, X-CNexus-Nonce",
        )
        self.end_headers()
        try:
            for chunk in generator:
                if not chunk:
                    continue
                data = chunk.encode("utf-8") if isinstance(chunk, str) else chunk
                self.wfile.write(data)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-CNexus-Signature, X-CNexus-Pubkey, X-CNexus-Timestamp, X-CNexus-Nonce",
        )
        self.end_headers()

    def _read_raw_body(self) -> bytes:
        if hasattr(self, "_raw_body_cached"):
            return self._raw_body_cached
        length = int(self.headers.get("Content-Length", 0))
        self._raw_body_cached = self.rfile.read(length) if length > 0 else b""
        return self._raw_body_cached

    def _read_json(self) -> dict:
        raw = self._read_raw_body()
        try:
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    def _get_post_data(self) -> dict:
        if hasattr(self, "_post_data_cached"):
            return self._post_data_cached
        raw = self._read_raw_body()
        try:
            self._post_data_cached = json.loads(raw) if raw else {}
        except Exception:
            self._post_data_cached = {}
        return self._post_data_cached

    def _serve_static(self, filepath: str) -> None:
        if not os.path.isfile(filepath):
            self._json({"ok": False, "error": f"File not found: {os.path.basename(filepath)}"}, 404)
            return
        ext = os.path.splitext(filepath)[1].lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".txt": "text/plain; charset=utf-8",
        }.get(ext, "application/octet-stream")
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _reject_websocket_upgrade(self) -> None:
        """Return 426 so browser WebSocket clients fail fast without retry loops."""
        self.send_response(426)
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"WebSocket not supported")
