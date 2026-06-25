"""Converse gateway — SSE lifecycle + deferred commit around CognitivePipeline."""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Iterator, Optional

from kernel.converse_events import ConverseEvent, ConverseEventType, converse_event
from kernel.pipeline import CognitivePipeline

from ..state import EngineStateManager

logger = logging.getLogger("cnexus.converse")


class ConverseService:
    """HTTP/SSE agnostic orchestrator — delegates cognition to CognitivePipeline."""

    def __init__(self, state: EngineStateManager, pipeline: CognitivePipeline):
        self._state = state
        self._pipeline = pipeline

    def stream_message(
        self,
        input_text: str,
        *,
        session_id: Optional[str] = None,
        model_id: Optional[str] = None,
        converse_mode: str = "fast",
        thinking_mode: str = "precision",
        memory_scope: str = "local",
    ) -> Iterator[ConverseEvent]:
        sid = session_id or "session-unknown"
        aborted = False
        fatal_error: Optional[Exception] = None
        turn_stream = self._pipeline.run_turn_stream(
            input_text,
            session_id=session_id,
            model_id=model_id,
            converse_mode=converse_mode,
            thinking_mode=thinking_mode,
            memory_scope=memory_scope,
        )

        try:
            for event in turn_stream:
                if event["event"] == ConverseEventType.META and isinstance(event["data"], dict):
                    sid = event["data"].get("session_id", sid)
                yield event

        except GeneratorExit:
            aborted = True
            logger.warning("Converse session %s aborted by client disconnect", sid)
            turn_stream.close()
            return

        except Exception as exc:
            fatal_error = exc
            logger.exception("Converse session %s failed", sid)
            yield converse_event(ConverseEventType.ERROR, f"Cognitive failure: {exc}")

        finally:
            if aborted:
                return
            done_payload = self._pipeline.last_done_payload
            commit_pkg = self._pipeline.last_commit
            if fatal_error is None and done_payload is not None:
                yield converse_event(ConverseEventType.DONE, done_payload)
            elif fatal_error is not None:
                yield converse_event(
                    ConverseEventType.DONE,
                    {"ok": False, "error": str(fatal_error), "session_id": sid},
                )
            else:
                yield converse_event(ConverseEventType.DONE, {"ok": False, "session_id": sid})
            if commit_pkg is not None and fatal_error is None:
                threading.Thread(
                    target=self._pipeline.commit_turn,
                    args=(commit_pkg,),
                    daemon=True,
                    name="cnexus-turn-commit",
                ).start()

    def run_blocking(
        self,
        input_text: str,
        *,
        model_id: Optional[str] = None,
        converse_mode: str = "fast",
        thinking_mode: str = "precision",
        memory_scope: str = "local",
    ) -> Dict[str, Any]:
        return self._pipeline.run_turn_blocking(
            input_text,
            model_id=model_id,
            converse_mode=converse_mode,
            thinking_mode=thinking_mode,
            memory_scope=memory_scope,
        )
