"""Pure cognitive loop — yields ConverseEvent, no HTTP."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, Optional, Protocol, Tuple

from kernel.converse_events import ConverseEvent, ConverseEventType, converse_event
from kernel.speak_reducer import _compose_kernel_reply


def _guard_reply_against_echo(input_text: str, reply: str) -> str:
    """Never return verbatim user text as assistant reply."""
    user = str(input_text or "").strip()
    out = str(reply or "").strip()
    if user and out == user:
        return _compose_kernel_reply(user, degradation_level="L0")
    return reply if out else _compose_kernel_reply(user, degradation_level="L0")


def _resolve_turn_llm_context(prep: Dict[str, Any], compose_llm_context: Callable[[str], str]) -> str:
    """When SCP admit ran, never bypass with raw activation_context (spec §11 PR gate)."""
    if "llm_context" in prep:
        return str(prep["llm_context"] or "")
    return compose_llm_context(str(prep.get("activation_context") or ""))


class StateAccess(Protocol):
    def mutate(self, fn: Callable[[Dict[str, Any]], Any]) -> Any: ...

    def get(self, key: str, default: Any = None) -> Any: ...


def cognize_context_dict(cog: Any) -> Any:
    ctx = getattr(cog, "context", cog)
    if hasattr(ctx, "state_snapshot"):
        return {
            k: getattr(ctx, k)
            for k in ("state_snapshot", "recall_items", "context_bundle", "observation_type")
            if hasattr(ctx, k)
        }
    return ctx


def _semantic_turn_meta(profile: Dict[str, Any], scp_response: Any) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "expert_mode": profile.get("expert_mode"),
        "style_source": profile.get("expert_style_source") or profile.get("style_source"),
        "thinking_mode": profile.get("thinking_mode"),
        "memory_scope": profile.get("memory_scope"),
        "scp_admitted": getattr(scp_response, "admitted", True),
    }
    decision = getattr(scp_response, "decision", None)
    if decision is not None:
        weights = getattr(decision, "dimension_weights", None)
        if weights:
            meta["dimension_weights"] = dict(weights)
    return meta


@dataclass(frozen=True)
class TurnCommitPackage:
    input_text: str
    obs: Any
    cog: Any
    dec: Any
    ctx: Any
    spk: Any
    model_row: Any
    llm_usage: Optional[Dict[str, Any]]
    token_source: str
    token_mode: str
    trace_id: str


@dataclass(frozen=True)
class PipelineDeps:
    observe: Callable[[str, Any], Any]
    cognize: Callable[[Any, Any, list], Any]
    decide: Callable[[Any, Any], Any]
    speak: Callable[[Any, Any, Any], Any]
    converse_mode_profile: Callable[[str], Dict[str, Any]]
    thinking_params: Callable[[str], Dict[str, Any]]
    touch_activity: Callable[[], None]
    resolve_model: Callable[[Optional[str]], Any]
    threshold_activated_fragments: Callable[..., list]
    format_activation_context: Callable[..., str]
    compose_llm_context: Callable[[str], str]
    runtime_context: Callable[[], str]
    memory_recall: Callable[[str, str], Dict[str, Any]]
    negotiation_conflict_context: Callable[[], Optional[str]]
    record_emergent_block_refs: Callable[[], None]
    should_use_external_llm: Callable[[Any], bool]
    iter_external_llm_stream: Callable[..., Iterator[Tuple[str, Any]]]
    invoke_external_llm: Callable[..., Dict[str, Any]]
    audit_thinking: Callable[..., None]
    speech_text: Callable[[Any], str]
    persist_turn: Callable[[TurnCommitPackage], None]
    fast_converse: bool
    scp_admit: Optional[Callable[[str, str, Dict[str, Any]], Any]] = None


class CognitivePipeline:
    """Six-step cognitive loop as a pure generator."""

    def __init__(self, state: StateAccess, deps: PipelineDeps):
        self._state = state
        self._deps = deps
        self.last_commit: Optional[TurnCommitPackage] = None
        self.last_done_payload: Optional[Dict[str, Any]] = None

    def prepare_turn(
        self,
        input_text: str,
        model_id: Optional[str],
        *,
        converse_mode: str = "fast",
        thinking_mode: str = "precision",
        memory_scope: str = "local",
        expert_mode: Optional[str] = None,
        expert_style_source: str = "prompt",
    ) -> Dict[str, Any]:
        deps = self._deps
        profile = deps.converse_mode_profile(converse_mode)
        profile = {
            **profile,
            **deps.thinking_params(thinking_mode),
            "memory_scope": memory_scope,
        }
        if expert_mode:
            profile["expert_mode"] = expert_mode
        profile["expert_style_source"] = expert_style_source
        deps.touch_activity()
        # Network/model registry work must stay outside the state lock (pre-architecture fast path).
        model_row = deps.resolve_model(model_id)
        light_prepare = deps.fast_converse and profile.get("mode") == "fast"

        def _prepare(engine: Dict[str, Any]) -> Dict[str, Any]:
            engine["current_iteration"] = int(engine.get("current_iteration", 0)) + 1
            trace_id = f"v2-trace-{engine['current_iteration']}"
            st = engine["state"]
            obs = deps.observe(input_text, st)
            cog = deps.cognize(obs, st, [])
            ctx = cognize_context_dict(cog)
            dec = deps.decide(ctx, st)
            activation_hits: list = []
            activation_context = ""
            runtime_context = deps.runtime_context()
            if light_prepare:
                pass
            elif profile.get("inject_memory"):
                activation_hits = deps.threshold_activated_fragments(
                    limit=profile.get("inject_limit"),
                    threshold=profile.get("activation_threshold"),
                    memory_scope=memory_scope,
                )
                activation_context = deps.format_activation_context(
                    activation_hits,
                    desc_max=profile.get("inject_desc_max"),
                )
                if profile.get("use_recall_supplement"):
                    recall_ctx = deps.memory_recall(input_text, memory_scope).get("context", "")
                    if recall_ctx and "未检索到" not in recall_ctx:
                        activation_context = (
                            f"{activation_context}\n---\n{recall_ctx}"
                            if activation_context
                            else recall_ctx
                        )
                elif profile.get("thinking_mode") == "emergent":
                    recall_ctx = deps.memory_recall(input_text, memory_scope).get("context", "")
                    if recall_ctx and "未检索到" not in recall_ctx:
                        activation_context = (
                            f"{activation_context}\n---\n{recall_ctx}"
                            if activation_context
                            else recall_ctx
                        )
                if profile.get("thinking_mode") == "emergent":
                    neg_ctx = deps.negotiation_conflict_context()
                    if neg_ctx:
                        deps.record_emergent_block_refs()
                        activation_context = (
                            f"{activation_context}\n---\n{neg_ctx}"
                            if activation_context
                            else neg_ctx
                        )
            if deps.scp_admit is not None:
                scp_response = deps.scp_admit(input_text, activation_context, profile)
                llm_context = getattr(scp_response, "llm_context", None)
                if llm_context is None and isinstance(scp_response, dict):
                    llm_context = scp_response.get("llm_context", "")
                if llm_context is None:
                    llm_context = deps.compose_llm_context(activation_context)
                engine["semantic_turn"] = _semantic_turn_meta(profile, scp_response)
                if hasattr(scp_response, "budget_state"):
                    engine["semantic_budget"] = scp_response.budget_state.to_dict()
                if hasattr(scp_response, "correction") and scp_response.correction is not None:
                    engine["semantic_budget_correction"] = {
                        "trigger_id": scp_response.correction.trigger_id,
                        "level": scp_response.correction.level,
                        "style_source_override": scp_response.correction.style_source_override,
                    }
            else:
                llm_context = deps.compose_llm_context(activation_context)
            return {
                "input_text": input_text,
                "trace_id": trace_id,
                "st": st,
                "obs": obs,
                "cog": cog,
                "ctx": ctx,
                "dec": dec,
                "model_row": model_row,
                "activation_hits": activation_hits,
                "activation_context": activation_context if profile.get("inject_memory") and not light_prepare else "",
                "llm_context": llm_context,
                "runtime_context": runtime_context,
                "mode_profile": profile,
                "thinking_mode": profile.get("thinking_mode", "precision"),
            }

        return self._state.mutate(_prepare)

    def commit_turn(self, package: TurnCommitPackage) -> None:
        self._deps.persist_turn(package)

    def run_turn_stream(
        self,
        input_text: str,
        *,
        session_id: Optional[str] = None,
        model_id: Optional[str] = None,
        converse_mode: str = "fast",
        thinking_mode: str = "precision",
        memory_scope: str = "local",
        expert_mode: Optional[str] = None,
        expert_style_source: str = "prompt",
    ) -> Iterator[ConverseEvent]:
        self.last_commit = None
        self.last_done_payload = None
        sid = session_id or f"session-{int(time.time() * 1000)}"
        t_start = time.perf_counter()
        user_causality = f"user_msg_{sid}"

        yield converse_event(
            ConverseEventType.STATUS,
            "Observing context...",
            step="observe",
            causality_id=user_causality,
        )
        prep = self.prepare_turn(
            input_text,
            model_id,
            converse_mode=converse_mode,
            thinking_mode=thinking_mode,
            memory_scope=memory_scope,
            expert_mode=expert_mode,
            expert_style_source=expert_style_source,
        )
        profile = prep["mode_profile"]
        t_prepare = time.perf_counter()

        yield converse_event(
            ConverseEventType.META,
            {
                "prepare_ms": round((t_prepare - t_start) * 1000),
                "activation_injected": len(prep["activation_hits"]),
                "trace_id": prep["trace_id"],
                "iteration": self._state.get("current_iteration"),
                "converse_mode": profile.get("mode", "fast"),
                "thinking_mode": profile.get("thinking_mode", "precision"),
                "memory_scope": profile.get("memory_scope", "local"),
                "global_entropy": profile.get("global_entropy"),
                "temperature": profile.get("temperature"),
                "session_id": sid,
            },
            step="observe",
            causality_id=prep["trace_id"],
        )

        model_row = prep["model_row"]
        dec, ctx, st = prep["dec"], prep["ctx"], prep["st"]
        activation_context = prep["activation_context"]
        llm_context = _resolve_turn_llm_context(prep, self._deps.compose_llm_context)
        token_source = "estimated"
        token_mode = "fast"
        llm_usage = None
        llm_error = None
        llm_source = "kernel"
        t_llm_start = time.perf_counter()
        reply = ""
        first_token_at = None
        spk: Any = None

        trace_id = prep["trace_id"]

        yield converse_event(
            ConverseEventType.STATUS,
            "Thinking...",
            step="decide",
            causality_id=trace_id,
        )

        if self._deps.should_use_external_llm(model_row):
            streamed_text = False
            try:
                llm_stream = self._deps.iter_external_llm_stream(
                    model_row,
                    input_text,
                    llm_context or None,
                    mode_profile=profile,
                )
                try:
                    for kind, payload in llm_stream:
                        if kind == "token":
                            chunk = str(payload or "")
                            if chunk.strip() and chunk.strip() == str(input_text or "").strip():
                                continue
                            if chunk:
                                streamed_text = True
                                if first_token_at is None:
                                    first_token_at = time.perf_counter()
                                yield converse_event(
                                    ConverseEventType.CHUNK,
                                    chunk,
                                    step="speak",
                                    causality_id=trace_id,
                                )
                        elif kind == "done":
                            llm_usage = payload
                            reply = payload["reply"]
                finally:
                    if hasattr(llm_stream, "close"):
                        llm_stream.close()
                reply = _guard_reply_against_echo(input_text, reply)
                if not streamed_text and reply:
                    first_token_at = first_token_at or time.perf_counter()
                    yield converse_event(
                        ConverseEventType.CHUNK,
                        reply,
                        step="speak",
                        causality_id=trace_id,
                    )
                token_source = "provider"
                llm_source = "provider"
                token_mode = str(model_row.get("model") or model_row.get("provider") or "llm")
                spk = {
                    "text": reply,
                    "inference_type": "llm",
                    "confidence": 0.9,
                    "latency_ms": 0,
                    "metadata": {
                        "provider": model_row.get("provider"),
                        "model_id": model_row.get("id"),
                        "stream": True,
                    },
                }
            except Exception as exc:
                llm_error = str(exc)
                spk = self._deps.speak(dec, ctx, st)
                spk = dict(spk) if isinstance(spk, dict) else {"text": str(spk)}
                spk["metadata"] = {**(spk.get("metadata") or {}), "llm_fallback": llm_error}
                reply = (
                    spk.get("text", spk.get("response_text", ""))
                    if isinstance(spk, dict)
                    else self._deps.speech_text(spk)
                )
                reply = _guard_reply_against_echo(input_text, reply)
                first_token_at = time.perf_counter()
                yield converse_event(
                    ConverseEventType.CHUNK,
                    reply,
                    step="speak",
                    causality_id=trace_id,
                )
        else:
            spk = self._deps.speak(dec, ctx, st)
            reply = (
                spk.get("text", spk.get("response_text", ""))
                if isinstance(spk, dict)
                else self._deps.speech_text(spk)
            )
            reply = _guard_reply_against_echo(input_text, reply)
            first_token_at = time.perf_counter()
            yield converse_event(
                ConverseEventType.CHUNK,
                reply,
                step="speak",
                causality_id=trace_id,
            )

        t_llm = time.perf_counter()
        if not reply:
            reply = (
                spk.get("text", spk.get("response_text", ""))
                if isinstance(spk, dict)
                else self._deps.speech_text(spk)
            )
        reply = _guard_reply_against_echo(input_text, reply)
        if isinstance(spk, dict):
            spk = {**spk, "text": reply}

        self._deps.audit_thinking(profile, prep["trace_id"], reply)

        yield converse_event(
            ConverseEventType.STATUS,
            "Consolidating memory...",
            step="reflect",
            causality_id=trace_id,
        )

        self.last_commit = TurnCommitPackage(
            input_text=prep["input_text"],
            obs=prep["obs"],
            cog=prep["cog"],
            dec=prep["dec"],
            ctx=prep["ctx"],
            spk=spk,
            model_row=model_row,
            llm_usage=llm_usage,
            token_source=token_source,
            token_mode=token_mode,
            trace_id=prep["trace_id"],
        )

        t_end = time.perf_counter()
        self.last_done_payload = {
            "ok": True,
            "reply": reply,
            "emotion": {
                "valence": prep["st"].emotion.val,
                "arousal": prep["st"].emotion.arousal,
                "dominance": prep["st"].emotion.dominance,
            },
            "intent": dec.get("intent", "converse"),
            "iteration": self._state.get("current_iteration"),
            "llm_source": llm_source,
            "llm_error": llm_error,
            "model_id": model_row.get("id") if model_row else None,
            "model_name": model_row.get("model") if model_row else None,
            "activation_injected": len(prep["activation_hits"]),
            "converse_mode": profile.get("mode", "fast"),
            "thinking_mode": profile.get("thinking_mode", "precision"),
            "memory_scope": profile.get("memory_scope", "local"),
            "global_entropy": profile.get("global_entropy"),
            "temperature": profile.get("temperature"),
            "latency_ms": {
                "prepare": round((t_prepare - t_start) * 1000),
                "llm": round((t_llm - t_llm_start) * 1000),
                "post": round((t_end - t_llm) * 1000),
                "total": round((t_end - t_start) * 1000),
                "ttft": round((first_token_at - t_prepare) * 1000) if first_token_at else 0,
            },
            "stream": True,
            "session_id": sid,
        }

    def run_turn_blocking(
        self,
        input_text: str,
        *,
        model_id: Optional[str] = None,
        converse_mode: str = "fast",
        thinking_mode: str = "precision",
        memory_scope: str = "local",
        expert_mode: Optional[str] = None,
        expert_style_source: str = "prompt",
    ) -> Dict[str, Any]:
        t_start = time.perf_counter()
        prep = self.prepare_turn(
            input_text,
            model_id,
            converse_mode=converse_mode,
            thinking_mode=thinking_mode,
            memory_scope=memory_scope,
            expert_mode=expert_mode,
            expert_style_source=expert_style_source,
        )
        profile = prep["mode_profile"]
        t_prepare = time.perf_counter()
        st = prep["st"]
        dec, ctx = prep["dec"], prep["ctx"]
        model_row = prep["model_row"]
        activation_hits = prep["activation_hits"]
        activation_context = prep["activation_context"]
        llm_context = _resolve_turn_llm_context(prep, self._deps.compose_llm_context)
        trace_id = prep["trace_id"]
        token_source = "estimated"
        token_mode = "fast"
        llm_usage = None
        llm_error = None
        llm_source = "kernel"

        if self._deps.should_use_external_llm(model_row):
            try:
                llm_usage = self._deps.invoke_external_llm(
                    model_row,
                    input_text,
                    llm_context or None,
                    mode_profile=profile,
                )
                spk = {
                    "text": llm_usage["reply"],
                    "inference_type": "llm",
                    "confidence": 0.9,
                    "latency_ms": 0,
                    "metadata": {"provider": model_row.get("provider"), "model_id": model_row.get("id")},
                }
                token_source = "provider"
                llm_source = "provider"
                token_mode = str(model_row.get("model") or model_row.get("provider") or "llm")
            except Exception as exc:
                llm_error = str(exc)
                spk = self._deps.speak(dec, ctx, st)
                spk = dict(spk) if isinstance(spk, dict) else {"text": str(spk)}
                spk["metadata"] = {**(spk.get("metadata") or {}), "llm_fallback": llm_error}
        else:
            spk = self._deps.speak(dec, ctx, st)

        t_llm = time.perf_counter()
        reply = (
            spk.get("text", spk.get("response_text", ""))
            if isinstance(spk, dict)
            else self._deps.speech_text(spk)
        )
        reply = _guard_reply_against_echo(input_text, reply)
        if isinstance(spk, dict):
            spk = {**spk, "text": reply}
        self._deps.audit_thinking(profile, trace_id, reply)

        self.commit_turn(
            TurnCommitPackage(
                input_text=prep["input_text"],
                obs=prep["obs"],
                cog=prep["cog"],
                dec=prep["dec"],
                ctx=prep["ctx"],
                spk=spk,
                model_row=model_row,
                llm_usage=llm_usage,
                token_source=token_source,
                token_mode=token_mode,
                trace_id=trace_id,
            )
        )
        t_end = time.perf_counter()

        return {
            "reply": reply,
            "emotion": {"valence": st.emotion.val, "arousal": st.emotion.arousal, "dominance": st.emotion.dominance},
            "intent": dec.get("intent", "converse"),
            "iteration": self._state.get("current_iteration"),
            "llm_source": llm_source,
            "llm_error": llm_error,
            "model_id": model_row.get("id") if model_row else None,
            "model_name": model_row.get("model") if model_row else None,
            "activation_injected": len(activation_hits),
            "activation_context": activation_context,
            "activation_hits": [
                {"id": spec["id"], "title": spec["title"], "score": round(score, 4)}
                for score, spec in activation_hits
            ],
            "converse_mode": profile.get("mode", "fast"),
            "thinking_mode": profile.get("thinking_mode", "precision"),
            "memory_scope": profile.get("memory_scope", "local"),
            "global_entropy": profile.get("global_entropy"),
            "temperature": profile.get("temperature"),
            "latency_ms": {
                "prepare": round((t_prepare - t_start) * 1000),
                "llm": round((t_llm - t_prepare) * 1000),
                "post": round((t_end - t_llm) * 1000),
                "total": round((t_end - t_start) * 1000),
            },
            "fast_converse": self._deps.fast_converse,
        }
