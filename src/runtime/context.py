"""Build fixed Runtime context — injected at BOOT, never recalled via vector search."""

from __future__ import annotations

from typing import List

from .types import CompiledRuntime, RuntimeDocument


def _format_documents(title: str, docs: List[RuntimeDocument]) -> str:
    if not docs:
        return ""
    lines = [f"## {title}"]
    for doc in docs:
        ver = f" v{doc.version}" if doc.version else ""
        lines.append(f"### {doc.title}{ver}")
        lines.append(doc.content.strip())
        lines.append("")
    return "\n".join(lines).strip()


def build_runtime_system_prompt(compiled: CompiledRuntime) -> str:
    """L5 Constitution + Runtime Policy — always prepended, never RAG."""
    parts: List[str] = [
        "【CNexus Runtime · BOOT Context】",
        "The following Constitution and Runtime Policy are fixed system rules.",
        "They are NOT searchable memory. Never ignore them. Never overwrite them.",
        "",
    ]
    constitution = _format_documents("L5 Constitution（认知宪法 · 系统契约）", compiled.constitution)
    if constitution:
        parts.append(constitution)
        parts.append("")
    policy = _format_documents("Runtime Policy（运行时策略）", compiled.policy)
    if policy:
        parts.append(policy)
    if len(parts) <= 4:
        return ""
    return "\n".join(parts).strip()


def build_memory_layer_preamble() -> str:
    """Reminder appended before subconscious memory injection."""
    return (
        "--- Subconscious Memory (L4 Foundation → L3 Project → L2 Memory → L1 Conversation) ---\n"
        "Prefer Foundation over Project over long-term memory. Constitution/Policy (Runtime) above all."
    )
