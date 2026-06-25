"""POST/GET auth gate — delegates to injected deny callback."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

DenyFn = Callable[..., Optional[Tuple[Any, int]]]
JsonResponse = Tuple[Any, int]


class AuthGate:
    """Central auth check for POST dispatch and protected GET routes."""

    def __init__(self, deny: DenyFn):
        self._deny = deny

    def check(
        self,
        path: str,
        headers: Any,
        body: Optional[Dict[str, Any]] = None,
        *,
        method: str = "POST",
    ) -> Optional[JsonResponse]:
        denied = self._deny(path, headers, body or {}, method=method)
        return denied

    def allow(self, handler: Any, path: str) -> bool:
        # Multipart uploads must keep rfile intact for parse_multipart downstream.
        ctype = (handler.headers.get("Content-Type") or "").lower()
        body = {} if "multipart/form-data" in ctype else handler._get_post_data()
        denied = self.check(path, handler.headers, body, method="POST")
        if denied is None:
            return True
        err, status = denied
        handler._json(err, status)
        return False
