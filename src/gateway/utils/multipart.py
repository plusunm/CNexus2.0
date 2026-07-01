"""Multipart form parsing for stdlib HTTP handlers."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Tuple

try:
    import cgi
except ModuleNotFoundError:  # Python 3.13+
    try:
        import legacy_cgi as cgi  # pip install legacy-cgi
    except ModuleNotFoundError:
        cgi = None  # type: ignore[assignment]


def _header_value(headers: Any, name: str) -> str:
    if not headers:
        return ""
    direct = headers.get(name) if hasattr(headers, "get") else None
    if direct:
        return str(direct)
    target = name.lower()
    if hasattr(headers, "items"):
        for key, value in headers.items():
            if str(key).lower() == target:
                return str(value)
    return ""


def _cgi_headers(headers: Any) -> dict[str, str]:
    if not headers:
        return {}
    if hasattr(headers, "items"):
        return {str(key).lower(): str(value) for key, value in headers.items()}
    return {str(key).lower(): str(value) for key, value in dict(headers).items()}


def parse_multipart(rfile, headers) -> Optional[Any]:
    if cgi is None:
        return None
    ctype = _header_value(headers, "Content-Type")
    if "multipart/form-data" not in ctype:
        return None
    length = _header_value(headers, "Content-Length")
    cgi_headers = _cgi_headers(headers)
    environ = {"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype}
    if length:
        environ["CONTENT_LENGTH"] = length
    return cgi.FieldStorage(
        fp=rfile,
        headers=cgi_headers,
        environ=environ,
        keep_blank_values=True,
    )


def read_uploaded_file(form: Any, field: str = "file") -> Tuple[Optional[bytes], Optional[str]]:
    if field not in form:
        return None, None
    file_item = form[field]
    if file_item is None or not getattr(file_item, "file", None):
        return None, None
    raw = file_item.file.read()
    filename = getattr(file_item, "filename", None) or "upload.txt"
    return raw, filename


def iter_uploaded_files(form: Any, *fields: str) -> list[Tuple[str, bytes]]:
    """Yield (filename, raw bytes) for every multipart file field."""
    names = fields or ("files", "file")
    out: list[Tuple[str, bytes]] = []
    for field in names:
        if field not in form:
            continue
        candidate = form[field]
        items = candidate if isinstance(candidate, list) else [candidate]
        for item in items:
            if item is None or isinstance(item, (bytes, str)):
                continue
            file_obj = getattr(item, "file", None)
            if file_obj is None:
                continue
            raw = file_obj.read()
            filename = getattr(item, "filename", None) or "upload.txt"
            out.append((filename, raw))
    return out
