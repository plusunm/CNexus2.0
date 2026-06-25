"""Shadow /v1 read projections — CSE, spine token, kernel records."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..state import EngineStateManager
from .converse_speech import decision_intent, speech_text
from .status_snapshot import StatusSnapshotService


def _iso_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())


def _estimate_tokens(text: Any) -> int:
    if not text:
        return 0
    return max(1, int(len(str(text)) * 0.75))


def _cost_level(total: int) -> str:
    if total < 400:
        return "low"
    if total < 1500:
        return "mid"
    if total < 4000:
        return "high"
    return "spike"


@dataclass(frozen=True)
class ShadowProjectionHooks:
    find_ollama_binary: Callable[[], Optional[str]]
    probe_ollama: Callable[[], bool]
    ollama_host: str
    active_chat_model_id: Callable[[], str]


class ShadowProjectionService:
    """Project engine trace/state into enterprise-shaped shadow read APIs."""

    def __init__(
        self,
        state: EngineStateManager,
        snapshot: StatusSnapshotService,
        hooks: ShadowProjectionHooks,
    ):
        self._state = state
        self._snapshot = snapshot
        self._hooks = hooks

    def api_logs(self, limit: int = 100) -> Dict[str, Any]:
        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            logs = engine.get("runtime_logs", [])
            tail = logs[-max(1, int(limit)) :]
            return {"logs": tail, "count": len(logs)}

        return self._state.mutate(_read)

    def gtbs_events(self, limit: int = 300) -> Dict[str, Any]:
        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            events = engine.get("gtbs_events", [])
            tail = events[-max(1, int(limit)) :]
            return {"events": tail, "count": len(events)}

        return self._state.mutate(_read)

    def ollama_status(self) -> Dict[str, Any]:
        binary = self._hooks.find_ollama_binary()
        running = self._hooks.probe_ollama()
        return {
            "installed": bool(binary),
            "binary_found": bool(binary),
            "running": running,
            "host": self._hooks.ollama_host,
            "download_url": "https://ollama.com/download",
            "binary_path": binary,
        }

    def ollama_start(self) -> Dict[str, Any]:
        if self._hooks.probe_ollama():
            return {"ok": True, "detail": "already_running", "running": True}
        binary = self._hooks.find_ollama_binary()
        if not binary:
            return {
                "ok": False,
                "detail": "not_installed",
                "running": False,
                "download_url": "https://ollama.com/download",
            }
        try:
            subprocess.Popen(
                [binary, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            time.sleep(1.2)
            running = self._hooks.probe_ollama()
            return {"ok": running, "detail": "started" if running else "start_failed", "running": running}
        except Exception as exc:
            return {"ok": False, "detail": str(exc), "running": False}

    def ollama_stop(self) -> Dict[str, Any]:
        if not self._hooks.probe_ollama():
            return {"ok": True, "detail": "already_stopped", "running": False}
        return {"ok": False, "detail": "externally_managed", "running": True}

    def execution_status(self) -> Dict[str, Any]:
        ollama = self.ollama_status()
        active_id = self._hooks.active_chat_model_id()

        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            active_row = (engine.get("model_registry") or {}).get(active_id, {})
            ollama_running = bool(ollama.get("running"))
            return {
                "active_chat_provider": active_id,
                "active_embed_provider": "ollama-local" if ollama_running else None,
                "providers": {
                    active_id: {
                        "state": "ready",
                        "capabilities": ["chat", "memory"],
                        "reachable": True,
                        "issues": [],
                        "details": {"provider": active_row.get("provider")},
                    },
                    "ollama": {
                        "state": "ready" if ollama_running else "offline",
                        "capabilities": ["embed", "chat"] if ollama_running else [],
                        "reachable": ollama_running,
                        "issues": [] if ollama_running else ["Ollama 服务未运行"],
                        "details": {"host": ollama.get("host")},
                    },
                },
                "suggested_actions": [] if ollama_running else ["start_ollama"],
                "embedding": {"active_mode": "ollama" if ollama_running else "hash"},
                "ollama": {
                    "running": ollama_running,
                    "installed": bool(ollama.get("installed")),
                    "binary_found": bool(ollama.get("binary_found")),
                    "host": ollama.get("host"),
                    "download_url": ollama.get("download_url"),
                    "binary_path": ollama.get("binary_path"),
                },
            }

        return self._state.mutate(_read)

    def cse_live(self, window: int = 200) -> Dict[str, Any]:
        return self._build_cognitive_output(window, mode="live")

    def cse_synthesize(self, window: int = 200) -> Dict[str, Any]:
        out = self._build_cognitive_output(window, mode="synth")
        out["narrative"] = "【重新分析】" + (out.get("narrative") or "")
        if out.get("discoveries"):
            out["discoveries"][0]["title"] = "合成分析 · " + out["discoveries"][0]["title"]
        return out

    def token_observatory(self, limit: int = 100) -> Dict[str, Any]:
        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            traces = list(reversed(engine.get("token_traces", [])))[: max(1, int(limit))]
            return {"token_traces": traces, "count": len(traces)}

        return self._state.mutate(_read)

    def runtime_introspect(self) -> Dict[str, Any]:
        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            traces = engine.get("token_traces", [])
            return {"token_traces": list(reversed(traces)), "count": len(traces)}

        return self._state.mutate(_read)

    def token_field(self, trace_id: str) -> Dict[str, Any]:
        entry = self._find_trace(trace_id)
        token_row = self._state.mutate(
            lambda engine: next(
                (t for t in reversed(engine.get("token_traces", [])) if t.get("trace_id") == trace_id),
                None,
            )
        )
        if not entry and not token_row:
            return {"detail": f"trace not found: {trace_id}"}

        inp = str((entry or {}).get("input") or "")
        reply = speech_text((entry or {}).get("speech"))
        tin = token_row.get("tokens_in") if token_row else _estimate_tokens(inp)
        tout = token_row.get("tokens_out") if token_row else _estimate_tokens(reply)
        total = tin + tout

        phases = ["observe", "cognize", "decide", "speak", "store", "reflect"]
        by_phase: Dict[str, int] = {}
        token_events: List[Dict[str, Any]] = []
        per_phase = max(1, total // len(phases))
        for i, phase in enumerate(phases):
            by_phase[phase] = per_phase
            token_events.append({
                "trace_id": trace_id,
                "event_id": f"{trace_id}-{phase}",
                "source": "personal_kernel",
                "tokens_in": per_phase if phase == "observe" else 0,
                "tokens_out": per_phase if phase == "speak" else 0,
                "total": per_phase,
                "phase": phase,
                "mode": "fast",
                "entry": f"{phase}_fn",
                "cost_level": _cost_level(per_phase),
                "timestamp": time.time() - (len(phases) - i) * 10,
            })

        return {
            "trace_id": trace_id,
            "total_cost": round(total * 0.0001, 6),
            "total_tokens": total,
            "field": {phase: float(by_phase[phase]) for phase in phases},
            "gradient": {phase: round(1.0 - i * 0.12, 2) for i, phase in enumerate(phases)},
            "by_phase": by_phase,
            "bindings": [{"spine_event_id": f"tx-{phase}", "tokens": by_phase[phase]} for phase in phases[:3]],
            "influence": {
                "hot_paths": [{"from": "observe", "to": "speak", "severity": "mid", "weight": 0.82}],
                "max_weight": 0.82,
            },
            "identity_id": "cnexus-2.0-personal",
            "token_events": token_events,
            "causal": {"nodes": [{"id": phase, "label": phase} for phase in phases], "edges": []},
        }

    def kernel_records_recent(self, limit: int = 20) -> Dict[str, Any]:
        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            traces = engine.get("trace", [])
            ids = [t.get("trace_id") for t in reversed(traces) if t.get("trace_id")]
            return {"trace_ids": ids[: max(1, int(limit))]}

        return self._state.mutate(_read)

    def kernel_record(self, trace_id: str) -> Optional[Dict[str, Any]]:
        entry = self._find_trace(trace_id)
        if not entry:
            return None
        steps = [
            ("observe", "观察输入"),
            ("cognize", "认知整合"),
            ("decide", "决策意图"),
            ("speak", "生成话语"),
            ("store", "写入记忆"),
            ("reflect", "反思调整"),
        ]
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        for i, (step, label) in enumerate(steps):
            node_id = f"{step}-{i}"
            nodes.append({"id": node_id, "label": label, "type": step, "phase": step})
            if i > 0:
                edges.append({"from": f"{steps[i - 1][0]}-{i - 1}", "to": node_id, "kind": "causal"})
        inp = str(entry.get("input") or "")
        reply = speech_text(entry.get("speech"))
        overview = self._snapshot.build()
        return {
            "version": "2.0-personal",
            "trace_id": trace_id,
            "intent_type": decision_intent(entry.get("decision")),
            "result": {"reply": reply, "input": inp},
            "identity": "CNexus 2.0 Personal",
            "graph_invariant": "personal-6step-v1",
            "graph": {"id": "personal-6step", "nodes": len(nodes), "edges": len(edges)},
            "nodes": nodes,
            "edges": edges,
            "state_projection": {
                "emotion": overview.get("emotion", {}),
                "goal": overview.get("goal", {}),
            },
            "causal_projection": {"links": edges},
            "explain_projection": {"summary": f"用户输入「{inp[:80]}」经 6 步认知循环后输出回复。"},
            "equivalence": None,
            "replay_signature": trace_id,
            "audit_log": {"source": "shadow_projection", "steps": len(steps)},
            "audit": {"ok": True, "edition": "personal"},
            "events": self._gtbs_events_for_trace(trace_id),
            "derivation": {"pipeline": "6-step-reducer", "iteration": entry.get("iteration")},
            "elapsed_ms": 48,
        }

    def kernel_learn(self, trace_id: str) -> Optional[Dict[str, Any]]:
        entry = self._find_trace(trace_id)
        if not entry:
            return None
        inp = str(entry.get("input") or "")
        reply = speech_text(entry.get("speech"))
        intent = decision_intent(entry.get("decision"))
        steps = [
            f"1. 观察：接收用户输入「{inp[:60]}」",
            "2. 认知：整合当前状态与上下文",
            f"3. 决策：确定意图为 {intent}",
            "4. 话语：生成内核回复",
            "5. 存储：写入 episodic / emotion 块",
            "6. 反思：调整下一轮认知权重",
        ]
        story = f"用户说「{inp[:80]}」，个人版内核经过 6 步离线认知循环，最终以「{reply[:80]}」回应。"
        return {
            "version": "2.0",
            "trace_id": trace_id,
            "execution_tier": "L0-personal",
            "mode": "fast",
            "summary": story,
            "steps": steps,
            "beginner_view": f"你问了：{inp[:100]}。CNexus 思考后回答：{reply[:100]}。",
            "intermediate_view": story,
            "expert_view": f"trace={trace_id} · intent={intent} · 6-step reducer chain · GTBS events=7",
            "execution_story": story,
            "memory_view": ["episodic block appended", "emotion snapshot updated"],
            "reasoning_trace": steps,
            "why_this_result": f"决策模块选择 intent={intent}，话语模块据此生成回复。",
            "why_it_feels_fast_or_slow": "个人版本地 reducer 无网络延迟，通常为毫秒级。",
            "mental_model": "观察→认知→决策→话语→存储→反思 六步循环",
            "user_intent_summary": inp[:200],
        }

    def _find_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        def _read(engine: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            for entry in reversed(engine.get("trace", [])):
                if entry.get("trace_id") == trace_id:
                    return entry
            return None

        return self._state.mutate(_read)

    def _gtbs_events_for_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        def _read(engine: Dict[str, Any]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for row in engine.get("gtbs_events", []):
                payload = row.get("payload") or {}
                prov = payload.get("provenance") or {}
                if prov.get("trace_id") == trace_id:
                    out.append(row)
            return out

        return self._state.mutate(_read)

    def _exec_traces_from_cycles(self, limit: int = 20) -> List[Dict[str, Any]]:
        def _read(engine: Dict[str, Any]) -> List[Dict[str, Any]]:
            traces = engine.get("trace", [])[-limit:]
            manifests: List[Dict[str, Any]] = []
            for entry in traces:
                manifests.append({
                    "trace_id": entry.get("trace_id", f"v2-trace-{entry.get('iteration', 0)}"),
                    "graph_id": "personal-6step",
                    "template_name": "chat_single_turn",
                    "status": "completed",
                })
            return manifests

        return self._state.mutate(_read)

    def _build_cognitive_output(self, window: int = 200, mode: str = "live") -> Dict[str, Any]:
        window = max(1, int(window or 200))

        def _read(engine: Dict[str, Any]) -> Dict[str, Any]:
            cycles = engine.get("trace", [])[-window:]
            st = engine["state"]
            ms = engine["memory_store"]
            iteration_count = engine.get("current_iteration", 0)
            memory_count = len(ms.blocks)
            valence = getattr(st.emotion, "val", 0.0)
            arousal = getattr(st.emotion, "arousal", 0.0)
            goal = (st.goal or {}).get("current", "探索")

            summary = [{
                "text": (
                    f"个人版 L0 内核已完成 {iteration_count} 次认知循环，"
                    f"当前记忆块 {memory_count} 个，系统状态 stable。"
                ),
                "confidence": 0.92,
                "source": "trace_projection",
            }]
            if cycles:
                last = cycles[-1]
                inp = str(last.get("input") or "")[:100]
                reply = speech_text(last.get("speech"))[:100]
                intent = decision_intent(last.get("decision"))
                summary.insert(0, {
                    "text": (
                        f"最近对话 trace={last.get('trace_id')} · 意图={intent} · "
                        f"用户「{inp}」→ 内核「{reply}」"
                    ),
                    "confidence": 0.9,
                    "source": "personal_kernel",
                })

            patterns = [{
                "text": f"情绪轨迹 valence={valence:.2f} arousal={arousal:.2f}，认知熵趋于稳定。",
                "confidence": 0.82,
                "source": "emotion_projection",
            }]
            if iteration_count >= 2:
                patterns.append({
                    "text": "连续对话后 episodic 写入稳定，6 步循环无异常拒绝。",
                    "confidence": 0.78,
                    "source": "store_projection",
                })

            insights = [{
                "title": "主脑深度思考中",
                "description": (
                    f"当前目标「{goal}」，个人版离线内核以 6 步 reducer 链运行，无需外部 LLM。"
                ),
                "confidence": 0.86,
                "why": "trace 投影显示 observe→reflect 全链路 commit 成功",
                "source": "personal_kernel",
                "novelty": 0.42,
                "evidence": [f"iteration={iteration_count}", f"memory_blocks={memory_count}"],
            }]
            if memory_count > 0:
                insights.append({
                    "title": "记忆网络正在生长",
                    "description": f"已索引 {memory_count} 个记忆块，记忆流图因子节点将随对话/上传持续增加。",
                    "confidence": 0.8,
                    "why": "BlockStore 非空",
                    "source": "memory_projection",
                    "novelty": 0.55,
                    "evidence": ["episodic store active"],
                })

            discoveries: List[Dict[str, Any]] = []
            if cycles:
                discoveries.append({
                    "id": f"disc-{cycles[-1].get('trace_id', 'latest')}",
                    "title": "新认知循环完成",
                    "description": f"trace {cycles[-1].get('trace_id')} 已通过 GTBS 7 事件投影。",
                    "confidence": 0.84,
                    "novelty": 0.7,
                    "why": "本轮为最新一次 6 步执行",
                    "evidence": [str(cycles[-1].get("input", ""))[:60]],
                    "source": "novel_trace",
                    "first_seen_at": _iso_ts(),
                })

            actions = [{
                "action": "continue_dialogue",
                "priority": 0.85,
                "rationale": "继续对话以积累 episodic 记忆并驱动流图脉冲",
                "category": "engagement",
                "impact": 0.75,
                "reversibility": 0.95,
                "why": "个人版最佳价值来自持续认知循环",
            }]
            if memory_count == 0:
                actions.insert(0, {
                    "action": "upload_document",
                    "priority": 0.9,
                    "rationale": "导入文档以填充记忆流图节点",
                    "category": "memory",
                    "impact": 0.8,
                    "reversibility": 0.9,
                    "why": "memory_items 为空，流图因子链尚未形成",
                })

            narrative_parts = [s["text"] for s in summary[:2]]
            if insights:
                narrative_parts.append(insights[0]["description"])
            narrative = " ".join(narrative_parts)
            trace_slice = engine.get("trace", [])[-20:]
            exec_traces = [
                {
                    "trace_id": entry.get("trace_id", f"v2-trace-{entry.get('iteration', 0)}"),
                    "graph_id": "personal-6step",
                    "template_name": "chat_single_turn",
                    "status": "completed",
                }
                for entry in trace_slice
            ]

            return {
                "summary": summary,
                "patterns": patterns,
                "insights": insights,
                "rules": [{
                    "text": "个人版使用内置 6 步认知内核，不依赖 Ollama 或外部 API Key。",
                    "confidence": 0.95,
                    "source": "policy",
                }],
                "experiences": [{
                    "text": f"已完成 {iteration_count} 次离线认知循环，治理状态 personal/stable。",
                    "confidence": 0.88,
                    "source": "experience:trace",
                }],
                "discoveries": discoveries,
                "actions": actions,
                "top_actions": actions[:1],
                "narrative": narrative,
                "generated_at": _iso_ts(),
                "window_size": window,
                "mode": mode,
                "exec_traces": exec_traces,
            }

        return self._state.mutate(_read)
