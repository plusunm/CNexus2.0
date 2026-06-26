"""REM consolidation synthesis — LLM + heuristic fact extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..llm import ExternalLlmService

ExtractKeywordsFn = Callable[[str, int], List[str]]
ResolveModelRowFn = Callable[[Optional[str]], Any]
LlmInvokeFn = Callable[[Any, str], Dict[str, Any]]

_REM_PROMPT = (
    "你是 CNexus 潜意识反思者。请阅读以下零散对话与记忆碎片，提炼 3-5 条高度浓缩、可长期复用的常识性事实。\n"
    "要求：每条一行，不要编号以外的多余解释；中文输出；避免重复；保留用户真实意图。\n\n"
    "{corpus}"
)


@dataclass(frozen=True)
class RemConsolidationSynthesisConfig:
    max_facts: int = 5
    max_sources: int = 24
    snippet_chars: int = 400


@dataclass(frozen=True)
class RemConsolidationSynthesisHooks:
    extract_keywords: ExtractKeywordsFn
    resolve_model_row: ResolveModelRowFn
    llm_invoke: LlmInvokeFn


def parse_consolidation_facts(raw_text: Any, *, max_facts: int = 5) -> List[str]:
    facts: List[str] = []
    for line in str(raw_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix in ("- ", "* ", "• "):
            if line.startswith(prefix):
                line = line[len(prefix) :].strip()
        line = line.lstrip("0123456789.) ").strip()
        if len(line) >= 6:
            facts.append(line[:320])
        if len(facts) >= max_facts:
            break
    return facts[:max_facts]


def heuristic_compact_facts(
    sources: List[Dict[str, Any]],
    *,
    extract_keywords: ExtractKeywordsFn,
    max_facts: int = 5,
) -> List[str]:
    facts: List[str] = []
    seen: set[str] = set()
    for src in sources:
        text = str(src.get("text") or "")
        snippet = text.split("\n", 1)[0].strip()
        if len(snippet) >= 8 and snippet not in seen:
            seen.add(snippet)
            facts.append(f"经对话沉淀：{snippet[:180]}")
        for kw in extract_keywords(text, 4):
            lowered = kw.lower()
            if lowered not in seen:
                seen.add(lowered)
                facts.append(f"用户关注主题：{kw}")
        if len(facts) >= max_facts:
            break
    return facts[:max_facts] or ["近期交互不足以形成新的长期常识节点"]


class RemConsolidationSynthesizer:
    """Synthesize REM semantic facts from compaction sources."""

    def __init__(
        self,
        hooks: RemConsolidationSynthesisHooks,
        *,
        config: Optional[RemConsolidationSynthesisConfig] = None,
    ):
        self._hooks = hooks
        self._config = config or RemConsolidationSynthesisConfig()

    def synthesize(self, sources: List[Dict[str, Any]]) -> List[str]:
        cfg = self._config
        hooks = self._hooks

        fragments: List[str] = []
        for i, src in enumerate(sources[: cfg.max_sources], 1):
            fragments.append(f"[{i}] {str(src.get('text') or '')[: cfg.snippet_chars]}")
        corpus = "\n".join(fragments)
        if not corpus.strip():
            return []

        model_row = hooks.resolve_model_row(None)
        if not ExternalLlmService.should_use_external(model_row):
            return heuristic_compact_facts(
                sources,
                extract_keywords=hooks.extract_keywords,
                max_facts=cfg.max_facts,
            )

        prompt = _REM_PROMPT.format(corpus=corpus)
        try:
            usage = hooks.llm_invoke(model_row, prompt)
            facts = parse_consolidation_facts(usage.get("reply", ""), max_facts=cfg.max_facts)
            if facts:
                return facts
        except Exception:
            pass

        return heuristic_compact_facts(
            sources,
            extract_keywords=hooks.extract_keywords,
            max_facts=cfg.max_facts,
        )
