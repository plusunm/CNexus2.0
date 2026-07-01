"""Minimal Card persistence — JSON file in CNEXUS_DATA_DIR."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

SCHEMA_VERSION = "1.0"
STORE_VERSION = "relationship-cards-v1"


class RelationshipCardStore:
    def __init__(self, *, cards_file: Callable[[], str], schedule_persist: Optional[Callable[[], None]] = None):
        self._cards_file = cards_file
        self._schedule_persist = schedule_persist
        self._lock = threading.Lock()

    def _path(self) -> str:
        return self._cards_file()

    def _load(self) -> Dict[str, Any]:
        path = self._path()
        if not os.path.isfile(path):
            return {"version": STORE_VERSION, "cards": []}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {"version": STORE_VERSION, "cards": []}
        if not isinstance(data, dict):
            return {"version": STORE_VERSION, "cards": []}
        cards = data.get("cards")
        if not isinstance(cards, list):
            data["cards"] = []
        data.setdefault("version", STORE_VERSION)
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        path = self._path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
        payload = {**data, "version": STORE_VERSION, "saved_at": time.time()}
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def list_cards(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._load().get("cards") or [])

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        for row in self.list_cards():
            meta = row.get("meta") if isinstance(row, dict) else None
            if isinstance(meta, dict) and meta.get("id") == card_id:
                return row
        return None

    def save_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
            cards: List[Dict[str, Any]] = list(data.get("cards") or [])
            meta = card.get("meta") if isinstance(card, dict) else {}
            card_id = meta.get("id") if isinstance(meta, dict) else None
            if card_id:
                cards = [row for row in cards if (row.get("meta") or {}).get("id") != card_id]
            cards.insert(0, card)
            data["cards"] = cards[:500]
            self._save(data)
        if self._schedule_persist:
            self._schedule_persist()
        return card

    def delete_card(self, card_id: str) -> bool:
        with self._lock:
            data = self._load()
            cards: List[Dict[str, Any]] = list(data.get("cards") or [])
            next_cards = [row for row in cards if (row.get("meta") or {}).get("id") != card_id]
            if len(next_cards) == len(cards):
                return False
            data["cards"] = next_cards
            self._save(data)
        return True

    @staticmethod
    def new_id() -> str:
        return f"rc-{uuid.uuid4().hex[:12]}"
