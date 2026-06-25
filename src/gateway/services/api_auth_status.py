"""API auth middleware status for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class ApiAuthStatusHooks:
    get_auth_middleware: Callable[[], Any]


class ApiAuthStatusService:
    def __init__(self, hooks: ApiAuthStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        mw = self._hooks.get_auth_middleware()
        if not mw:
            return {"enabled": False}
        return {
            "enabled": True,
            "required_mode": mw.auth_required_enabled(),
            "max_skew_seconds": mw.max_skew_seconds(),
            "protected_post_paths": sorted(mw.PROTECTED_POST_PATHS),
            "strict_peer_paths": sorted(mw.STRICT_PEER_PATHS),
            "headers": [
                mw.HEADER_SIGNATURE,
                mw.HEADER_PUBKEY,
                mw.HEADER_TIMESTAMP,
            ],
        }
