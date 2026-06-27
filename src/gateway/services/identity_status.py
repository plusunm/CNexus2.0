"""Node identity (Ed25519) status for L0 snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class IdentityStatusHooks:
    identity_optional: bool
    identity_key_path: Callable[[], str]
    get_identity_manager: Callable[[], Any]
    identity_load_error: Callable[[], str] = lambda: ""


class IdentityStatusService:
    def __init__(self, hooks: IdentityStatusHooks):
        self._hooks = hooks

    def build(self) -> Dict[str, Any]:
        im = self._hooks.get_identity_manager()
        err = str(self._hooks.identity_load_error() or "").strip()
        if im is None:
            hint = ""
            if err == "missing_pynacl":
                hint = "pip install pynacl"
            elif err.startswith("invalid_identity_key"):
                hint = "delete identity.key and restart CNexus"
            return {
                "enabled": not self._hooks.identity_optional,
                "loaded": False,
                "algorithm": "Ed25519",
                "path": self._hooks.identity_key_path(),
                "error": err or ("missing_pynacl" if not self._hooks.identity_optional else ""),
                "hint": hint or ("pip install pynacl" if not self._hooks.identity_optional else ""),
            }
        return {
            "enabled": True,
            "loaded": True,
            "algorithm": "Ed25519",
            "pubkey": im.public_key_hex(),
            "path": self._hooks.identity_key_path(),
        }
