"""Text helpers for ingest and memory indexing."""

from __future__ import annotations

import re
from typing import List


def extract_keywords(text: str, limit: int = 6) -> List[str]:
    if not text:
        return []
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", str(text))
    seen: set[str] = set()
    out: List[str] = []
    for tok in tokens:
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok[:24])
        if len(out) >= limit:
            break
    return out


def decode_upload_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")
