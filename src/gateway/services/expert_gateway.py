"""Gateway adapter for expert distillation plugin."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..state import EngineStateManager


class ExpertGatewayService:
    def __init__(
        self,
        state: EngineStateManager,
        *,
        schedule_persist: Callable[[], None],
        resolve_model: Optional[Callable[[], Any]] = None,
        llm_invoke: Optional[Callable[[Any, str], Dict[str, Any]]] = None,
    ):
        self._state = state
        self._schedule_persist = schedule_persist
        self._resolve_model = resolve_model
        self._llm_invoke = llm_invoke
        self._service = None

    def _svc(self):
        if self._service is None:
            from plugins.expert_distill.distill import ExpertDistillEngine
            from plugins.expert_distill.service import ExpertDistillService

            engine = ExpertDistillEngine(
                resolve_model=self._resolve_model,
                llm_invoke=self._llm_invoke,
            )
            self._service = ExpertDistillService(
                self._state.mutate_memory_store,
                lambda: list(self._state.mutate(lambda e: e["memory_store"].blocks)),
                schedule_persist=self._schedule_persist,
                distill_engine=engine,
            )
        return self._service

    def list_subjects(self) -> Dict[str, Any]:
        return {"ok": True, "subjects": self._svc().list_subjects()}

    def distill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data or {})
        modes = payload.get("modes")
        if isinstance(modes, str):
            modes = [m.strip() for m in modes.split(",") if m.strip()]
        return self._svc().run_distill(
            subject_id=str(payload.get("subject_id") or ""),
            modes=modes,
        )

    def fact_confirm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._svc().confirm_fact(str((data or {}).get("block_id") or ""))

    def capture(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data or {})
        return self._svc().capture_for_subject(
            subject_id=str(payload.get("subject_id") or ""),
            content=str(payload.get("content") or payload.get("text") or ""),
            semantic_dimension=str(payload.get("semantic_dimension") or "fact"),
            layer=str(payload.get("layer") or "semantic"),
        )
