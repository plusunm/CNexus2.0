"""Catalog interest filter — topics, owners, graph_ids."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, Optional

try:
    from protocol.models import CatalogEntry
except ImportError:
    from cnexus_protocol.models import CatalogEntry


@dataclass(frozen=True)
class CatalogInterest:
    topics: tuple[str, ...] = ()
    owners: tuple[str, ...] = ()
    graph_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "CatalogInterest":
        row = data or {}
        return cls(
            topics=tuple(str(x).strip() for x in (row.get("topics") or []) if str(x).strip()),
            owners=tuple(str(x).strip().lower() for x in (row.get("owners") or []) if str(x).strip()),
            graph_ids=tuple(str(x).strip().lower() for x in (row.get("graph_ids") or []) if str(x).strip()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "topics": list(self.topics),
            "owners": list(self.owners),
            "graph_ids": list(self.graph_ids),
        }

    def is_empty(self) -> bool:
        return not (self.topics or self.owners or self.graph_ids)


def filter_entries_by_interest(entries: Iterable[CatalogEntry], interest: CatalogInterest) -> List[CatalogEntry]:
    if interest.is_empty():
        return list(entries)
    out: List[CatalogEntry] = []
    topic_set = {t.lower() for t in interest.topics}
    owner_set = {o.lower() for o in interest.owners}
    graph_set = {g.lower() for g in interest.graph_ids}
    for entry in entries:
        if graph_set and entry.graph_id.lower() in graph_set:
            out.append(entry)
            continue
        if owner_set and entry.owner.lower() in owner_set:
            out.append(entry)
            continue
        if topic_set and entry.topic.lower() in topic_set:
            out.append(entry)
            continue
    return out
