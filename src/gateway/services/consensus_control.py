"""Consensus reputation control APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

JsonResponse = Tuple[Any, int]


@dataclass(frozen=True)
class ConsensusControlHooks:
    get_reputation_registry: Callable[[], Any]
    get_network_firewall: Callable[[], Any]
    audit_event: Callable[..., None]


class ConsensusControlService:
    def __init__(self, hooks: ConsensusControlHooks):
        self._hooks = hooks

    def update_reputation(self, data: Dict[str, Any]) -> JsonResponse:
        rep = self._hooks.get_reputation_registry()
        if rep is None:
            return {"ok": False, "error": "reputation_unavailable"}, 503
        payload = data or {}
        pubkey = str(payload.get("pubkey") or payload.get("peer_pubkey") or "").strip()
        action = str(payload.get("action") or "").strip().lower()
        if not pubkey:
            return {"ok": False, "error": "missing_pubkey"}, 400
        if action in ("blacklist", "ban"):
            row = rep.set_blacklisted(pubkey, blacklisted=True, reason=str(payload.get("reason") or "ui_blacklist"))
            fw = self._hooks.get_network_firewall()
            if fw and action == "ban":
                try:
                    fw.ban_peer(pubkey, reason=str(payload.get("reason") or "ui_ban"))
                except Exception:
                    pass
        elif action in ("restore", "unblacklist"):
            row = rep.restore_peer(pubkey, trust_score=float(payload.get("trust_score") or 0.55))
        else:
            return {"ok": False, "error": "unsupported_action"}, 400
        self._hooks.audit_event("consensus.reputation", {"pubkey": pubkey[:64], "action": action})
        return {"ok": True, "pubkey": pubkey, "reputation": row or rep.get_all().get(pubkey)}, 200
