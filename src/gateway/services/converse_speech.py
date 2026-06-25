"""Speech / decision text helpers shared across converse pipeline."""

from __future__ import annotations

from typing import Any


def speech_text(speech: Any) -> str:
    if speech is None:
        return ""
    if isinstance(speech, dict):
        return str(speech.get("text") or speech.get("response_text") or "")
    for attr in ("text", "response_text"):
        if hasattr(speech, attr):
            return str(getattr(speech, attr) or "")
    return str(speech)


def decision_intent(decision: Any) -> str:
    if isinstance(decision, dict):
        return str(decision.get("intent", "converse"))
    if hasattr(decision, "intent"):
        return str(getattr(decision, "intent", "converse"))
    return "converse"
