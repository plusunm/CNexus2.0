"""MemoryRemService — REM deep-sleep orchestration (P4-E)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ...state import EngineStateManager
from .graph import MemoryGraphService
from .rem_synthesis import RemConsolidationSynthesizer

GetRemEngineFn = Callable[[], Any]
ExtractKeywordsFn = Callable[[str, int], List[str]]
SpeechTextFn = Callable[[Dict[str, Any]], str]
AppendRuntimeLogFn = Callable[..., None]
SchedulePersistFn = Callable[[], None]
GetCognitivePruningEngineFn = Callable[[], Any]


@dataclass(frozen=True)
class MemoryRemConfig:
    activation_threshold: float = 0.4
    activation_max_score: float = 1.0


@dataclass(frozen=True)
class MemoryRemHooks:
    get_rem_engine: GetRemEngineFn
    extract_keywords: ExtractKeywordsFn
    speech_text: SpeechTextFn
    append_runtime_log: AppendRuntimeLogFn
    schedule_persist: SchedulePersistFn
    get_cognitive_pruning_engine: GetCognitivePruningEngineFn


class MemoryRemService:
    """Gateway REM orchestration — context assembly, cycle callbacks, watchdog."""

    def __init__(
        self,
        state: EngineStateManager,
        graph: MemoryGraphService,
        hooks: MemoryRemHooks,
        synthesizer: RemConsolidationSynthesizer,
        *,
        config: Optional[MemoryRemConfig] = None,
    ):
        self._state = state
        self._graph = graph
        self._hooks = hooks
        self._synthesizer = synthesizer
        self._config = config or MemoryRemConfig()

    def build_context(self) -> Dict[str, Any]:
        snap = self._graph.rem_graph_snapshot()

        def enrich(engine: Dict[str, Any]):
            trace_out: List[Dict[str, Any]] = []
            for entry in engine.get("trace", []):
                row = dict(entry)
                row["reply_text"] = self._hooks.speech_text(entry.get("speech") or {})
                trace_out.append(row)
            consolidation = engine.setdefault("consolidation", {})
            return trace_out, consolidation

        trace, consolidation = self._state.mutate(enrich)
        return {
            "now": time.time(),
            "specs": snap["specs"],
            "scores": snap["scores"],
            "adjacency": snap["adjacency"],
            "protected_ids": snap["protected_ids"],
            "trace": trace,
            "consolidation": consolidation,
            "activation_threshold": self._config.activation_threshold,
        }

    def consolidation_status(self, consolidation: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        engine = self._hooks.get_rem_engine()
        if engine is None:
            return {"enabled": False}
        return engine.status(consolidation, ctx)

    def run_deep_sleep(self, *, force: bool = False) -> Dict[str, Any]:
        engine = self._hooks.get_rem_engine()
        if engine is None:
            return {"ok": False, "error": "rem_engine_unavailable"}

        ctx = self.build_context()
        trace_id = f"rem-{int(time.time())}"
        hooks = self._hooks
        cfg = self._config

        def on_finish(report: Dict[str, Any]) -> None:
            if not report.get("ok"):
                return
            hooks.append_runtime_log(
                (
                    f"REM深度睡眠 · pruned={report.get('pruned_nodes', 0)} "
                    f"traces={report.get('pruned_traces', 0)} facts={report.get('facts_created', 0)}"
                ),
                category="cognition",
                trace_id=trace_id,
            )

            def reanchor(engine: Dict[str, Any]) -> None:
                scores = engine.setdefault("activation", {}).setdefault("scores", {})
                if "goal-current" in scores:
                    scores["goal-current"] = max(float(scores.get("goal-current", 0.0)), 0.35)
                for block in engine["memory_store"].blocks:
                    block_id = str(block.get("block_id", ""))
                    if block_id.startswith("sem-rem-"):
                        scores[block_id] = cfg.activation_max_score

            self._state.mutate(reanchor)

            prune = hooks.get_cognitive_pruning_engine()
            if prune and prune.enabled:
                prune_report = prune.run_cycle(dry_run=False)
                if prune_report.get("archived_blocks") or prune_report.get("summaries_created"):
                    hooks.append_runtime_log(
                        (
                            f"认知修剪 · archived={prune_report.get('archived_blocks', 0)} "
                            f"summaries={prune_report.get('summaries_created', 0)}"
                        ),
                        category="cognition",
                        trace_id=trace_id,
                    )

        report = engine.run_rem_cycle(
            ctx,
            force=force,
            synthesize_fn=self._synthesizer.synthesize,
            add_block_fn=self._add_semantic_block,
            remove_traces_fn=self._remove_traces,
            remove_blocks_fn=self._remove_blocks_for_iterations,
            on_finish=on_finish,
        )
        if report.get("error"):
            hooks.append_runtime_log(
                f"REM深度睡眠失败 · {report.get('error')}",
                category="cognition",
                level="error",
                trace_id=trace_id,
            )
        hooks.schedule_persist()
        return report

    def start_watchdog(self) -> None:
        threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="cnexus-rem-watchdog",
        ).start()

    def _watchdog_loop(self) -> None:
        engine = self._hooks.get_rem_engine()
        if engine is None or not engine.enabled:
            return
        while True:
            try:
                time.sleep(engine.watchdog_interval)
                ctx = self.build_context()
                if engine.should_trigger(ctx.get("consolidation") or {}, ctx):
                    self.run_deep_sleep(force=False)
            except Exception:
                pass

    def _add_semantic_block(self, block: Dict[str, Any]) -> None:
        hooks = self._hooks
        cfg = self._config

        def apply(engine: Dict[str, Any]) -> None:
            ms = engine["memory_store"]
            data = dict(block.get("data") or {})
            content = str(data.get("content") or "")
            keywords = hooks.extract_keywords(content, 5)
            data["keywords"] = keywords
            block_copy = dict(block)
            block_copy["data"] = data
            ms.add(block_copy)
            scores = engine.setdefault("activation", {}).setdefault("scores", {})
            block_id = str(block_copy.get("block_id") or "")
            scores[block_id] = cfg.activation_max_score
            for kw in keywords:
                scores[f"kw-{block_id}-{kw}"] = min(cfg.activation_max_score, 0.75)

        self._state.mutate(apply)

    def _remove_blocks_for_iterations(self, iterations) -> int:
        def apply(engine: Dict[str, Any]) -> int:
            removed = 0
            it_set = {int(i) for i in iterations}
            ms = engine["memory_store"]
            kept = []
            for block in ms.blocks:
                block_id = str(block.get("block_id", ""))
                drop = False
                if block_id.startswith("ep:it"):
                    try:
                        if int(block_id.split("ep:it", 1)[1]) in it_set:
                            drop = True
                    except Exception:
                        pass
                if not drop:
                    for it in it_set:
                        if block_id.startswith(f"kw-ep:it{it}-"):
                            drop = True
                            break
                if drop:
                    removed += 1
                else:
                    kept.append(block)
            ms.blocks = kept
            return removed

        return self._state.mutate(apply)

    def _remove_traces(self, trace_ids, iterations) -> int:
        def apply(engine: Dict[str, Any]) -> int:
            trace = engine.get("trace", [])
            id_set = set(trace_ids)
            it_set = {int(i) for i in iterations}
            kept = []
            removed = 0
            for entry in trace:
                tid = entry.get("trace_id")
                it = int(entry.get("iteration", 0))
                if tid in id_set or it in it_set:
                    removed += 1
                else:
                    kept.append(entry)
            engine["trace"] = kept
            return removed

        return self._state.mutate(apply)
