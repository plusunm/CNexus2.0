"""Expert multi-mode distillation — fact / style / decision (SSS-aligned)."""

from __future__ import annotations

import os
import re
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .tagging import stamp_expert_metadata

LlmInvokeFn = Callable[[Any, str], Dict[str, Any]]
ResolveModelFn = Callable[[], Any]

_DISTILL_PROMPTS = {
    "fact": (
        "你是 CNexus 专家事实蒸馏器。阅读语料，为 subject「{subject}」提炼 3-5 条可审计事实。\n"
        "要求：每条一行；中文；不得编造语料中不存在的内容。\n\n{corpus}"
    ),
    "style": (
        "你是 CNexus 专家风格蒸馏器。阅读语料，总结 subject「{subject}」的表达风格（语气、结构、修辞）。\n"
        "要求：3-5 条；每条一行；这是风格指南，不是事实。\n\n{corpus}"
    ),
    "decision": (
        "你是 CNexus 决策模式蒸馏器。阅读语料，提炼 subject「{subject}」的决策优先级与 IF-THEN 模式。\n"
        "要求：3-5 条；每条一行；标注为决策模式，不是历史事实。\n\n{corpus}"
    ),
}

_LABEL_FOR_MODE = {"fact": "semantic", "style": "narrative", "decision": "belief"}


def _block_text(block: Mapping[str, Any]) -> str:
    data = dict(block.get("data") or {})
    return str(data.get("content") or data.get("response_text") or "").strip()


def _subject_corpus(blocks: Sequence[Mapping[str, Any]], subject_id: str, *, max_chars: int = 6000) -> str:
    parts: List[str] = []
    total = 0
    for block in blocks:
        data = dict(block.get("data") or {})
        sid = str(data.get("subject_id") or data.get("expert_id") or "").strip()
        if sid and sid != subject_id:
            continue
        text = _block_text(block)
        if len(text) < 8:
            continue
        chunk = text[:800]
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n---\n".join(parts)


def _parse_lines(raw: Any, *, max_items: int = 5) -> List[str]:
    lines: List[str] = []
    for line in str(raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix in ("- ", "* ", "• "):
            if line.startswith(prefix):
                line = line[len(prefix) :].strip()
        line = line.lstrip("0123456789.) ").strip()
        if len(line) >= 6:
            lines.append(line[:320])
        if len(lines) >= max_items:
            break
    return lines


def _heuristic_distill(mode: str, corpus: str, *, max_items: int = 4) -> List[str]:
    if not corpus.strip():
        return []
    sentences = [s.strip() for s in re.split(r"[。！？\n]+", corpus) if len(s.strip()) >= 10]
    if mode == "style":
        return [f"表达偏好：{s[:120]}" for s in sentences[:max_items]]
    if mode == "decision":
        return [f"决策倾向：{s[:120]}" for s in sentences[:max_items]]
    return [f"事实要点：{s[:120]}" for s in sentences[:max_items]]


class ExpertDistillEngine:
    """Produce distilled blocks — writes to BlockStore via callback."""

    def __init__(
        self,
        *,
        resolve_model: Optional[ResolveModelFn] = None,
        llm_invoke: Optional[LlmInvokeFn] = None,
    ):
        self._resolve_model = resolve_model
        self._llm_invoke = llm_invoke

    def distill(
        self,
        blocks: Sequence[Mapping[str, Any]],
        *,
        subject_id: str,
        modes: Sequence[str],
    ) -> List[Dict[str, Any]]:
        subject = str(subject_id or "").strip()
        if not subject:
            return []
        corpus = _subject_corpus(blocks, subject)
        if not corpus.strip():
            corpus = _subject_corpus(blocks, subject, max_chars=12000) or "\n".join(
                _block_text(b)[:200] for b in blocks[:12] if _block_text(b)
            )

        out_blocks: List[Dict[str, Any]] = []
        ts = time.time()
        for mode in modes:
            m = str(mode or "fact").strip().lower()
            if m not in _DISTILL_PROMPTS:
                continue
            items = self._distill_mode(subject, m, corpus)
            label = _LABEL_FOR_MODE.get(m, "semantic")
            for i, item in enumerate(items):
                block = stamp_expert_metadata(
                    {
                        "label": label,
                        "block_id": f"expert-{subject.replace(':', '-')}-{m}-{int(ts)}-{i}",
                        "data": {"content": item, "filename": f"expert:{m}"},
                        "importance": 0.82 if m == "fact" else 0.72,
                        "timestamp": ts,
                    },
                    subject_id=subject,
                    semantic_dimension=m if m != "decision" else "decision",
                    distill_mode=m,
                )
                if m == "fact":
                    block["data"]["fact_confirm_required"] = True
                out_blocks.append(block)
        return out_blocks

    def _distill_mode(self, subject: str, mode: str, corpus: str) -> List[str]:
        prompt_tpl = _DISTILL_PROMPTS[mode]
        prompt = prompt_tpl.format(subject=subject, corpus=corpus[:5000])
        if self._resolve_model and self._llm_invoke:
            try:
                model = self._resolve_model()
                if model and model.get("enabled", True):
                    usage = self._llm_invoke(model, prompt)
                    parsed = _parse_lines(usage.get("reply"))
                    if parsed:
                        return parsed
            except Exception:
                pass
        return _heuristic_distill(mode, corpus)
