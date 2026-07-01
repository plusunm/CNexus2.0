"""POST /api/analyze — canonical relationship analysis orchestration."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional

from .relationship_canonical import (
    extract_json_object,
    merge_llm_fill,
    normalize_llm_payload,
    rule_based_analysis,
    to_card_envelope,
    validate_analysis,
)
from .relationship_cards import RelationshipCardStore

logger = logging.getLogger("cnexus.relationship_analyze")


class RelationshipAnalyzeService:
    def __init__(
        self,
        *,
        card_store: RelationshipCardStore,
        converse_blocking: Callable[..., Dict[str, Any]],
        status_snapshot: Callable[[], Dict[str, Any]],
        resolve_model: Callable[[], Any],
        llm_service: Optional[Any] = None,
        llm_enabled: bool = True,
    ):
        self._cards = card_store
        self._converse_blocking = converse_blocking
        self._status_snapshot = status_snapshot
        self._resolve_model = resolve_model
        self._llm_service = llm_service
        self._llm_enabled = llm_enabled

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        source_input = str(data.get("text") or data.get("sourceInput") or data.get("input") or "").strip()
        if not source_input:
            return {"ok": False, "error": "missing text"}

        fast = bool(data.get("fast", False))
        use_llm = bool(data.get("use_llm", True)) and self._llm_enabled and not fast
        save_card = data.get("save_card", True) is not False
        degraded = False

        if fast:
            converse: Dict[str, Any] = {}
        else:
            try:
                converse = self._converse_blocking(
                    source_input,
                    converse_mode=str(data.get("converse_mode") or "deep"),
                    thinking_mode=str(data.get("thinking_mode") or "precision"),
                )
            except Exception:
                logger.warning("analyze converse failed — degrading to rule baseline", exc_info=True)
                converse = {}
                fast = True
                use_llm = False
                degraded = True

        status = self._status_snapshot()
        analysis_id = RelationshipCardStore.new_id()
        baseline = rule_based_analysis(source_input, converse, status, analysis_id=analysis_id)

        fill_source = "rule"
        if use_llm and self._llm_service:
            try:
                llm_payload = self._llm_fill(source_input, converse, status, baseline)
                if llm_payload:
                    baseline = merge_llm_fill(baseline, llm_payload)
                    fill_source = "llm+rule"
            except Exception:
                logger.warning("LLM fill failed — using rule baseline", exc_info=True)

        validate_analysis(baseline)
        model_fill_source = "rule"
        model_payload: Optional[Dict[str, Any]] = None
        if use_llm and self._llm_service:
            try:
                model_payload = self._llm_model_compress(baseline)
                if model_payload:
                    model_fill_source = "llm+rule"
            except Exception:
                logger.warning("Model card LLM compress failed — using rule baseline", exc_info=True)

        card = to_card_envelope(baseline, model_payload)
        if save_card:
            self._cards.save_card(card)

        return {
            "ok": True,
            "analysis": baseline,
            "card": card,
            "fill_source": fill_source,
            "model_fill_source": model_fill_source,
            "fast": fast,
            "degraded": degraded,
        }

    def list_cards(self) -> Dict[str, Any]:
        cards = self._cards.list_cards()
        return {"ok": True, "cards": cards, "count": len(cards)}

    def get_card(self, card_id: str) -> Dict[str, Any]:
        row = self._cards.get_card(card_id)
        if not row:
            return {"ok": False, "error": "not found"}
        return {"ok": True, "card": row}

    def delete_card(self, data: Dict[str, Any]) -> Dict[str, Any]:
        card_id = str(data.get("id") or data.get("card_id") or "").strip()
        if not card_id:
            return {"ok": False, "error": "missing id"}
        deleted = self._cards.delete_card(card_id)
        return {"ok": deleted, "deleted": deleted, "id": card_id}

    def analyze_timeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Event Ontology → Timeline → State Engine → CanonicalSchema (+ optional card)."""
        from .relationship_cards import RelationshipCardStore
        from .relationship_cognitive_pipeline import run_cognitive_pipeline

        conversation = data.get("conversation")
        if not isinstance(conversation, list) or len(conversation) == 0:
            return {"ok": False, "error": "missing conversation"}

        entities = data.get("entities")
        if entities is not None and (not isinstance(entities, list) or len(entities) < 2):
            return {"ok": False, "error": "entities must be [A, B]"}

        save_card = data.get("save_card", False) is not False
        use_llm = bool(data.get("use_llm", True)) and self._llm_enabled
        analysis_id = RelationshipCardStore.new_id()

        try:
            pipeline = run_cognitive_pipeline(
                conversation,
                entities=entities,
                analysis_id=analysis_id,
                source_input=str(data.get("sourceInput") or data.get("source_input") or "").strip() or None,
            )
        except Exception as exc:
            logger.exception("analyze_timeline pipeline failed")
            return {"ok": False, "error": f"pipeline failed: {exc}"}

        analysis = pipeline["analysis"]
        validate_analysis(analysis)

        model_fill_source = "rule"
        card = None
        if save_card:
            model_payload: Optional[Dict[str, Any]] = None
            if use_llm and self._llm_service:
                try:
                    model_payload = self._llm_model_compress(analysis)
                    if model_payload:
                        model_fill_source = "llm+rule"
                except Exception:
                    logger.warning("timeline model card LLM failed", exc_info=True)
            card = to_card_envelope(analysis, model_payload)
            self._cards.save_card(card)

        return {
            "ok": True,
            "eventStream": pipeline["eventStream"],
            "timeline": pipeline["timeline"],
            "relationshipState": pipeline["relationshipState"],
            "analysis": analysis,
            "card": card,
            "pipeline_source": "rule",
            "model_fill_source": model_fill_source if save_card else None,
        }

    def _llm_fill(
        self,
        source_input: str,
        converse: Dict[str, Any],
        status: Dict[str, Any],
        baseline: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        from .llm import ExternalLlmService
        from .relationship_llm_prompt import RELATIONSHIP_LLM_FILL_SYSTEM, build_llm_fill_user_prompt

        model_row = self._resolve_model()
        if not model_row or not ExternalLlmService.should_use_external(model_row):
            return None

        context = {
            "reply": converse.get("reply"),
            "emotion": converse.get("emotion"),
            "intent": converse.get("intent"),
            "activation_injected": converse.get("activation_injected"),
            "activation_hits": converse.get("activation_hits"),
            "activation_context": converse.get("activation_context"),
            "relationship": status.get("relationship") or converse.get("relationship"),
            "baseline_state": baseline.get("state"),
        }
        user_prompt = build_llm_fill_user_prompt(
            source_input,
            json.dumps(context, ensure_ascii=False, default=str),
        )
        messages = ExternalLlmService.build_simple_messages(RELATIONSHIP_LLM_FILL_SYSTEM, user_prompt)
        result = self._llm_service.invoke_messages(
            model_row,
            messages,
            mode_profile={"temperature": 0.15, "thinking_mode": "precision"},
        )
        parsed = extract_json_object(str(result.get("reply") or ""))
        if not parsed:
            return None
        normalized = normalize_llm_payload(parsed)
        return normalized if normalized else None

    def _llm_model_compress(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from .llm import ExternalLlmService
        from .relationship_card_llm_prompt import (
            RELATIONSHIP_CARD_MODEL_SYSTEM,
            build_card_model_user_prompt,
        )
        from .relationship_model_ontology import (
            ontology_template_for_prompt,
            route_model,
        )

        model_row = self._resolve_model()
        if not model_row or not ExternalLlmService.should_use_external(model_row):
            return None

        route = route_model(analysis)
        template = ontology_template_for_prompt(str(route.get("familyId") or "generic"))

        user_prompt = build_card_model_user_prompt(
            json.dumps(analysis, ensure_ascii=False, default=str),
            route=route,
            library_template=template,
        )
        messages = ExternalLlmService.build_simple_messages(RELATIONSHIP_CARD_MODEL_SYSTEM, user_prompt)
        result = self._llm_service.invoke_messages(
            model_row,
            messages,
            mode_profile={"temperature": 0.1, "thinking_mode": "precision"},
        )
        parsed = extract_json_object(str(result.get("reply") or ""))
        if not parsed:
            return None
        return parsed
