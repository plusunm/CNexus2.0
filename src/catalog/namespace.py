"""Catalog Bloom namespaces — catalog/system, catalog/topic/X, catalog/owner/Y."""

from __future__ import annotations

from typing import Iterable, List, Optional

try:
    from protocol.models import CatalogEntry
except ImportError:
    from cnexus_protocol.models import CatalogEntry


def normalize_namespace(value: str) -> str:
    ns = str(value or "").strip().lower().strip("/")
    if not ns:
        return "catalog/system"
    if not ns.startswith("catalog/"):
        ns = f"catalog/{ns}"
    return ns


def namespace_for_entry(entry: CatalogEntry) -> str:
    topic = str(entry.topic or "").strip()
    if topic:
        return normalize_namespace(f"topic/{topic}")
    owner = str(entry.owner or "").strip()
    if owner:
        return normalize_namespace(f"owner/{owner[:16]}")
    return "catalog/system"


def filter_entries_by_namespace(entries: Iterable[CatalogEntry], namespace: str) -> List[CatalogEntry]:
    ns = normalize_namespace(namespace)
    if ns in ("catalog/system", "catalog/all"):
        return list(entries)
    prefix = ns + "/"
    out: List[CatalogEntry] = []
    for entry in entries:
        entry_ns = namespace_for_entry(entry)
        if entry_ns == ns or entry_ns.startswith(prefix):
            out.append(entry)
    return out
