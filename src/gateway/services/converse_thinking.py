"""Thinking-mode inference + system prompt builders — gateway-owned."""

from __future__ import annotations

from typing import Any, Dict

THINKING_MODES = frozenset({"precision", "emergent"})


def format_entropy_seed(seed: int) -> str:
    mask = (1 << 64) - 1
    return hex(int(seed or 0) & mask)


def temperature_from_seed(seed: int, *, base: float = 0.7, spread: float = 0.3) -> float:
    bucket = int(seed or 0) % 1000
    return round(base + (bucket / 1000.0) * spread, 3)


def normalize_thinking_mode(raw: Any) -> str:
    mode = str(raw or "precision").strip().lower()
    if mode in ("emergent", "creative", "explore", "associative"):
        return "emergent"
    if mode in ("precision", "strict", "deterministic", "exact"):
        return "precision"
    return "precision"


def thinking_inference_params(thinking_mode: str, global_entropy: int) -> Dict[str, Any]:
    entropy = int(global_entropy or 0)
    entropy_hex = format_entropy_seed(entropy)
    if normalize_thinking_mode(thinking_mode) == "emergent":
        return {
            "thinking_mode": "emergent",
            "temperature": temperature_from_seed(entropy),
            "use_reflection": True,
            "provenance_enforced": False,
            "global_entropy": entropy_hex,
            "global_entropy_int": entropy,
        }
    return {
        "thinking_mode": "precision",
        "temperature": 0.0,
        "use_reflection": False,
        "provenance_enforced": True,
        "global_entropy": entropy_hex,
        "global_entropy_int": entropy,
    }


def build_emergent_system_content(user_text: str, memory_context: str, global_entropy: int) -> str:
    entropy_hex = format_entropy_seed(int(global_entropy or 0))
    ctx = (memory_context or "").strip() or "(无关联记忆)"
    question = str(user_text or "").strip()
    return (
        f"[SYSTEM_MODE: EMERGENT | ENTROPY: {entropy_hex}]\n"
        "你现在处于“涌现智慧”模式。你可以结合本地与远程关联记忆进行创造性联想。\n\n"
        "护栏约束：\n"
        "1. 必须明确标注哪些内容是基于原始审计日志的（事实），哪些是基于跨节点联想的（涌现结论）。\n"
        "2. 如果你的涌现结论与原始审计事实冲突，必须在回复末尾显式通过 "
        '"Reflection Log:" 标注这种冲突。\n\n'
        f"用户问题: {question}\n\n"
        "--- 关联记忆 ---\n"
        f"{ctx}"
    )


def build_precision_system_content(memory_context: str, *, provenance_preamble: str = "") -> str:
    ctx = (memory_context or "").strip()
    parts = [
        "You are CNexus 2.0 personal cognitive assistant.",
        "Mode: PRECISION — treat audit-backed memory as authoritative; do not invent facts.",
    ]
    if provenance_preamble:
        parts.append(provenance_preamble.strip())
    if ctx:
        parts.append("--- Subconscious Memory (spreading activation, instant recall) ---")
        parts.append(ctx)
    return "\n".join(parts)
