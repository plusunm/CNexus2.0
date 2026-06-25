"""Post-speak turn persistence — store, reflect, trace, GTBS, audit, token trace."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from kernel.pipeline import TurnCommitPackage

from ..state import EngineStateManager
from .audit_emitter import AuditEmitter
from .converse_speech import speech_text

StoreFn = Callable[[Any, Any, Any, Any], Any]
ReflectFn = Callable[[Any, Any, Any, Any], Any]
SignRecordFn = Callable[[Dict[str, Any]], Any]
RecordCycleGtbsFn = Callable[[int, str, str, Any, Any, Any], None]
ScheduleActivationFn = Callable[[str, str, str], None]
RecordTokenTraceFn = Callable[..., None]
SchedulePersistFn = Callable[[], None]


@dataclass(frozen=True)
class TurnPersistenceHooks:
    store: StoreFn
    reflect: ReflectFn
    sign_record: SignRecordFn
    record_cycle_gtbs: RecordCycleGtbsFn
    schedule_activation_post_turn: ScheduleActivationFn
    record_token_trace: RecordTokenTraceFn
    schedule_persist: SchedulePersistFn


class TurnPersistenceService:
    """Finalize a converse turn under EngineStateManager lock."""

    def __init__(self, state: EngineStateManager, hooks: TurnPersistenceHooks, audit: AuditEmitter):
        self._state = state
        self._hooks = hooks
        self._audit = audit

    @staticmethod
    def reply_text(package: TurnCommitPackage) -> str:
        spk = package.spk
        if isinstance(spk, dict):
            return str(spk.get("text", spk.get("response_text", "")))
        return speech_text(spk)

    def commit_turn(self, package: TurnCommitPackage) -> None:
        hooks = self._hooks

        def _finalize(engine: Dict[str, Any]) -> None:
            st = engine["state"]
            ms = engine["memory_store"]
            iteration_meta = {"iteration": engine["current_iteration"], **package.obs}
            sto = hooks.store(package.spk, st, iteration_meta, ms)
            trace_tail = engine.get("trace", [])[-3:]
            rfl = hooks.reflect(sto, st, trace_tail, ms)

            engine.setdefault("trace", []).append(
                {
                    "iteration": engine["current_iteration"],
                    "trace_id": package.trace_id,
                    "timestamp": time.time(),
                    "input": package.input_text,
                    "observation": package.obs,
                    "cognition": package.cog,
                    "decision": package.dec,
                    "speech": package.spk,
                    "store": sto,
                    "reflection": rfl,
                }
            )
            trace_row = engine["trace"][-1]
            signed_trace = hooks.sign_record(trace_row)
            if signed_trace:
                trace_row["identity"] = signed_trace
            self._audit.event(
                "trace.cycle",
                {
                    "trace_id": trace_row["trace_id"],
                    "iteration": trace_row["iteration"],
                    "input_preview": (package.input_text or "")[:240],
                    "intent": package.dec.get("intent") if isinstance(package.dec, dict) else None,
                },
            )
            hooks.record_cycle_gtbs(
                engine["current_iteration"],
                package.trace_id,
                package.input_text,
                package.dec,
                package.spk,
                sto,
            )
            reply = self.reply_text(package)
            hooks.schedule_activation_post_turn(package.input_text, reply, package.trace_id)
            if package.llm_usage:
                hooks.record_token_trace(
                    package.trace_id,
                    package.input_text,
                    reply,
                    entry="converse",
                    mode=package.token_mode,
                    tokens_in=package.llm_usage["tokens_in"],
                    tokens_out=package.llm_usage["tokens_out"],
                    source="provider",
                    model_id=package.llm_usage.get("model_id"),
                    provider=package.llm_usage.get("provider"),
                )
            else:
                hooks.record_token_trace(
                    package.trace_id,
                    package.input_text,
                    reply,
                    entry="converse",
                    mode=package.token_mode,
                    source=package.token_source,
                    model_id=package.model_row.get("id") if package.model_row else None,
                    provider=(package.model_row or {}).get("provider"),
                )

        self._state.mutate(_finalize)
        hooks.schedule_persist()
