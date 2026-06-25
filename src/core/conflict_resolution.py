"""Adversarial memory conflict resolution — emergent merge or forked narrative."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional

from core.entropy import (
    derive_global_entropy,
    format_entropy_seed,
    parse_entropy_seed,
    temperature_from_seed,
)

LlmFn = Callable[[str, str, float], Optional[str]]


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def conflict_resolution_enabled() -> bool:
    return _env_truthy("CNEXUS_CONFLICT_RESOLUTION", default=True)


def normalize_content(text: str) -> str:
    return " ".join(str(text or "").split()).strip().lower()


def entry_from_block(block: dict, *, source: str = "local") -> Dict[str, Any]:
    data = dict((block or {}).get("data") or {})
    return {
        "block_id": str((block or {}).get("block_id") or ""),
        "label": str((block or {}).get("label") or "episode"),
        "content": str(data.get("content") or data.get("content_preview") or ""),
        "source": source,
        "source_peer": str(data.get("source_peer") or ""),
        "provenance": str(data.get("provenance") or ""),
    }


def entry_from_audit_data(data: dict, *, source: str = "remote") -> Dict[str, Any]:
    row = dict(data or {})
    return {
        "block_id": str(row.get("block_id") or ""),
        "label": str(row.get("label") or "episode"),
        "content": str(row.get("content_preview") or row.get("content") or ""),
        "source": source,
        "source_peer": str(row.get("source_peer") or ""),
        "provenance": str(row.get("provenance") or ""),
    }


def entries_conflict(local: dict, remote: dict) -> bool:
    local_text = normalize_content(local.get("content"))
    remote_text = normalize_content(remote.get("content"))
    if not local_text or not remote_text:
        return False
    return local_text != remote_text


def _token_set(text: str) -> set[str]:
    return {token for token in re.split(r"[^\w\u4e00-\u9fff]+", text) if token}


def _overlap_ratio(a: str, b: str) -> float:
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta | tb), 1)


def _extract_json_object(text: str) -> Optional[dict]:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


class ConflictResolutionAgent:
    """Resolve contradictory memory fragments via heuristic or adversarial LLM synthesis."""

    def __init__(self, *, default_mode: str = "emergent"):
        mode = str(default_mode or "emergent").strip().lower()
        self.default_mode = mode if mode in ("precision", "emergent") else "emergent"

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": conflict_resolution_enabled(),
            "default_mode": self.default_mode,
            "modes": ["precision", "emergent"],
        }

    def resolve(
        self,
        local_entry: dict,
        remote_entry: dict,
        *,
        mode: Optional[str] = None,
        seed: Optional[int] = None,
        peer_pubkeys: Optional[List[str]] = None,
        use_llm: Optional[bool] = None,
        llm_fn: Optional[LlmFn] = None,
    ) -> Dict[str, Any]:
        mode = str(mode or self.default_mode).strip().lower()
        if mode not in ("precision", "emergent"):
            mode = self.default_mode

        local = dict(local_entry or {})
        remote = dict(remote_entry or {})
        report: Dict[str, Any] = {
            "ok": False,
            "mode": mode,
            "block_id": local.get("block_id") or remote.get("block_id"),
            "phase": "resolve",
            "resolved_at": time.time(),
        }

        if not entries_conflict(local, remote):
            report.update({
                "ok": True,
                "status": "aligned",
                "merged_content": local.get("content") or remote.get("content"),
                "rationale": "entries_are_compatible",
            })
            return report

        if seed is not None:
            entropy = int(seed)
        elif peer_pubkeys:
            entropy = derive_global_entropy(local_seed=0, peer_pubkeys=peer_pubkeys)
        else:
            entropy = 0
        temperature = temperature_from_seed(entropy)
        report["entropy_seed"] = hex(entropy)
        report["temperature"] = temperature

        should_llm = use_llm if use_llm is not None else (mode == "emergent")
        if should_llm and llm_fn is not None:
            llm_report = self._llm_resolve(local, remote, entropy=entropy, temperature=temperature, llm_fn=llm_fn)
            if llm_report.get("ok"):
                report.update(llm_report)
                report["source"] = "llm"
                return report

        heuristic = self._heuristic_resolve(
            local,
            remote,
            conservative=(mode == "precision"),
            entropy=entropy,
        )
        report.update(heuristic)
        report["source"] = "heuristic"
        return report

    def _heuristic_resolve(
        self,
        local: dict,
        remote: dict,
        *,
        conservative: bool,
        entropy: int,
    ) -> Dict[str, Any]:
        local_text = str(local.get("content") or "").strip()
        remote_text = str(remote.get("content") or "").strip()
        overlap = _overlap_ratio(local_text, remote_text)

        if local_text and remote_text and (local_text in remote_text or remote_text in local_text):
            merged = remote_text if len(remote_text) >= len(local_text) else local_text
            return {
                "ok": True,
                "status": "merged",
                "merged_content": merged,
                "rationale": "one_entry_subsumes_the_other",
                "overlap": round(overlap, 4),
            }

        if not conservative and overlap >= 0.55:
            merged = (
                f"{local_text}\n"
                f"---\n"
                f"[Synthesized overlap · seed={hex(entropy)[-8:]}]\n"
                f"{remote_text}"
            )
            return {
                "ok": True,
                "status": "merged",
                "merged_content": merged[:2000],
                "rationale": f"high_token_overlap_{overlap:.2f}",
                "overlap": round(overlap, 4),
            }

        return {
            "ok": True,
            "status": "forked",
            "merged_content": "",
            "fork": {
                "local": local_text,
                "remote": remote_text,
                "label": "分叉叙事",
            },
            "rationale": "irreconcilable_without_llm" if conservative else "low_overlap_fork",
            "overlap": round(overlap, 4),
        }

    def _llm_resolve(
        self,
        local: dict,
        remote: dict,
        *,
        entropy: int,
        temperature: float,
        llm_fn: LlmFn,
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are CNexus ConflictResolutionAgent. Given two contradictory memory fragments, "
            "produce a JSON object only — no markdown fences.\n"
            'Schema: {"status":"merged|forked","merged_content":"...","rationale":"...",'
            '"fork_local":"...","fork_remote":"..."}\n'
            "Rules:\n"
            "1. Find factual overlap first.\n"
            "2. If contradictions remain, either synthesize a third explanation (merged) "
            "or keep both versions (forked).\n"
            "3. Never invent facts absent from A or B."
        )
        user_prompt = (
            f"Block ID: {local.get('block_id') or remote.get('block_id')}\n"
            f"Entropy seed: {hex(entropy)}\n"
            f"Temperature hint: {temperature}\n\n"
            f"A (local):\n{local.get('content')}\n\n"
            f"B (remote / peer={remote.get('source_peer') or 'unknown'}):\n{remote.get('content')}\n"
        )
        try:
            raw = llm_fn(system_prompt, user_prompt, temperature) or ""
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        parsed = _extract_json_object(raw)
        if not parsed:
            return {"ok": False, "error": "llm_unparseable"}

        status = str(parsed.get("status") or "").strip().lower()
        if status not in ("merged", "forked"):
            return {"ok": False, "error": "llm_invalid_status"}

        merged_content = str(parsed.get("merged_content") or "").strip()
        rationale = str(parsed.get("rationale") or "llm_resolution").strip()
        if status == "merged" and not merged_content:
            return {"ok": False, "error": "llm_missing_merged_content"}

        report: Dict[str, Any] = {
            "ok": True,
            "status": status,
            "merged_content": merged_content[:2000],
            "rationale": rationale,
            "llm_raw": raw[:1200],
        }
        if status == "forked":
            report["fork"] = {
                "local": str(parsed.get("fork_local") or local.get("content") or ""),
                "remote": str(parsed.get("fork_remote") or remote.get("content") or ""),
                "label": "分叉叙事",
            }
        return report


def apply_resolution_to_block(block: dict, resolution: dict) -> dict:
    """Return updated memory block after conflict resolution."""
    row = dict(block or {})
    data = dict(row.get("data") or {})
    status = str((resolution or {}).get("status") or "")
    if status == "merged":
        merged = str(resolution.get("merged_content") or "").strip()
        if merged:
            data["content"] = merged[:2000]
            data["provenance"] = "merged"
            data["content_kind"] = "full"
            data["conflict_resolved"] = True
            data["conflict_status"] = "merged"
            data["conflict_rationale"] = resolution.get("rationale")
    elif status == "forked":
        fork = dict(resolution.get("fork") or {})
        data["content"] = (
            f"[分叉叙事]\n"
            f"A(local): {fork.get('local', '')}\n"
            f"B(remote): {fork.get('remote', '')}"
        )[:2000]
        data["provenance"] = "forked"
        data["content_kind"] = "preview"
        data["conflict_resolved"] = True
        data["conflict_status"] = "forked"
        data["fork"] = fork
        data["conflict_rationale"] = resolution.get("rationale")
    row["data"] = data
    row["label"] = str(row.get("label") or "episode")
    if status in ("merged", "forked"):
        row["label"] = "conflict_resolved"
    return row
