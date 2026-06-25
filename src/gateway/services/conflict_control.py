"""Conflict resolution control APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

JsonResponse = Tuple[Any, int]


@dataclass(frozen=True)
class ConflictControlHooks:
    get_conflict_agent: Callable[[], Any]
    run_conflict_resolution: Callable[..., Dict[str, Any]]
    conflict_resolution_status: Callable[[], Dict[str, Any]]
    set_negotiation_conflict_llm: Callable[[bool], None]
    set_negotiation_conflict_enabled: Callable[[bool], None]


class ConflictControlService:
    def __init__(self, hooks: ConflictControlHooks):
        self._hooks = hooks

    def resolve(self, data: Dict[str, Any] | None = None) -> JsonResponse:
        payload = data or {}
        mode = str(payload.get("mode") or payload.get("thinking_mode") or "emergent").strip().lower()
        if mode in ("precision", "deterministic", "strict"):
            mode = "precision"
        else:
            mode = "emergent"

        use_llm = payload.get("use_llm", mode == "emergent")
        if isinstance(use_llm, str):
            use_llm = use_llm.lower() not in ("0", "false", "no")

        apply_flag = payload.get("apply", True)
        if isinstance(apply_flag, str):
            apply_flag = apply_flag.lower() not in ("0", "false", "no")

        mod = self._hooks.get_conflict_agent()
        if not mod:
            return {"ok": False, "error": "conflict_resolution_unavailable"}, 503

        local_raw = payload.get("local") or payload.get("local_entry") or {}
        remote_raw = payload.get("remote") or payload.get("remote_entry") or {}
        if isinstance(local_raw, str):
            local_entry = {"block_id": payload.get("block_id", ""), "content": local_raw, "source": "local"}
        else:
            local_entry = mod.entry_from_block(local_raw, source="local") if local_raw.get("data") else dict(local_raw)
        if isinstance(remote_raw, str):
            remote_entry = {"block_id": payload.get("block_id", ""), "content": remote_raw, "source": "remote"}
        else:
            remote_entry = (
                mod.entry_from_audit_data(remote_raw, source="remote")
                if remote_raw.get("content_preview") or remote_raw.get("block_id")
                else dict(remote_raw)
            )

        if not local_entry.get("content") or not remote_entry.get("content"):
            return {"ok": False, "error": "missing_local_or_remote_content"}, 400

        seed = payload.get("entropy_seed") or payload.get("seed")
        parsed_seed = None
        if seed is not None:
            try:
                parsed_seed = int(seed, 16) if isinstance(seed, str) and seed.startswith("0x") else int(seed)
            except (TypeError, ValueError):
                parsed_seed = None

        report = self._hooks.run_conflict_resolution(
            local_entry,
            remote_entry,
            mode=mode,
            use_llm=bool(use_llm),
            apply=bool(apply_flag),
            seed=parsed_seed,
        )
        code = 200 if report.get("ok") else 502 if report.get("error") else 400
        return report, code

    def update_settings(self, data: Dict[str, Any]) -> JsonResponse:
        payload = data or {}
        if "llm_auto_resolve" in payload:
            self._hooks.set_negotiation_conflict_llm(bool(payload.get("llm_auto_resolve")))
        if "auto_resolve_enabled" in payload:
            self._hooks.set_negotiation_conflict_enabled(bool(payload.get("auto_resolve_enabled")))
        status = self._hooks.conflict_resolution_status()
        return {
            "ok": True,
            "llm_auto_resolve": status.get("negotiation_conflict_llm"),
            "auto_resolve_enabled": status.get("negotiation_conflict_enabled"),
            "runtime_override": status.get("negotiation_conflict_llm_runtime"),
            "auto_resolve_runtime": status.get("negotiation_conflict_enabled_runtime"),
            "conflict_resolution": status,
        }, 200
