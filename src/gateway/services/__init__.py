"""Gateway domain services — lazy exports avoid ingest ↔ __init__ cycles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .converse import ConverseService
    from .ingest import DocumentIngestService
    from .models import ModelConfigService

__all__ = ["ConverseService", "DocumentIngestService", "ModelConfigService"]


def __getattr__(name: str):
    if name == "ConverseService":
        from .converse import ConverseService

        return ConverseService
    if name == "DocumentIngestService":
        from .ingest import DocumentIngestService

        return DocumentIngestService
    if name == "ModelConfigService":
        from .models import ModelConfigService

        return ModelConfigService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
