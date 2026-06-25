"""Static SPA file serving for Next.js export."""

from __future__ import annotations

import glob
import os
import re
from typing import Optional

from ..http.responses import HttpRouteResponse

_ASSET_EXTS = (
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".json",
    ".svg",
    ".ico",
    ".map",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
)

_MIME_BY_EXT = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}


class StaticRouteHandler:
    """Next.js static export + SPA fallback — always returns a response."""

    def __init__(self, ui_dir: str):
        self._ui_dir = ui_dir

    def handle_get(self, path: str) -> HttpRouteResponse:
        clean_path = path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"
        local_path = os.path.join(self._ui_dir, clean_path)

        if os.path.isdir(local_path):
            local_path = os.path.join(local_path, "index.html")

        if os.path.isfile(local_path):
            return _file_response(local_path)

        chunk_match = _resolve_next_chunk(clean_path, local_path)
        if chunk_match is not None:
            return _file_response(chunk_match)

        if any(clean_path.endswith(ext) for ext in _ASSET_EXTS):
            return HttpRouteResponse.json({"ok": False, "error": f"Asset not found: {path}"}, 404)

        fallback = os.path.join(self._ui_dir, "index.html")
        if os.path.isfile(fallback):
            return _file_response(fallback)

        return HttpRouteResponse.json({"ok": False, "error": "index.html missing"}, 500)


def _resolve_next_chunk(clean_path: str, local_path: str) -> Optional[str]:
    if not clean_path.startswith("_next/static/chunks/"):
        return None
    basename = os.path.basename(clean_path)
    dirpart = os.path.dirname(local_path)
    pattern = re.sub(r"^(\d+)(\.\w+)$", r"\1.*\2", basename)
    if basename == pattern:
        return None
    matches = glob.glob(os.path.join(dirpart, pattern))
    return matches[0] if matches else None


def _file_response(filepath: str) -> HttpRouteResponse:
    if not os.path.isfile(filepath):
        return HttpRouteResponse.json(
            {"ok": False, "error": f"File not found: {os.path.basename(filepath)}"},
            404,
        )
    ext = os.path.splitext(filepath)[1].lower()
    content_type = _MIME_BY_EXT.get(ext, "application/octet-stream")
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except Exception as exc:
        return HttpRouteResponse.json({"ok": False, "error": str(exc)}, 500)
    return HttpRouteResponse.bytes(data, content_type)
