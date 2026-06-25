#!/usr/bin/env python3
"""Smoke-check frontend ↔ backend integration contracts on a live gateway."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:7864"

CHECKS: list[tuple[str, str, list[str]]] = [
    ("GET", "/api/status", ["memory_items", "cards", "feeds", "system", "chat_context", "generated_at"]),
    ("GET", "/v1/health", ["status"]),
    ("GET", "/v1/gateway/health", []),
    ("GET", "/v1/system/capability", []),
    ("GET", "/v1/execution/status", []),
    ("GET", "/v1/cse/live?window=50", []),
    ("GET", "/logs?limit=5", ["logs"]),
]

CARD_KEYS = ["goal", "identity", "belief", "focus"]
FEED_KEYS = ["episodic", "reflections", "changes"]
SYSTEM_KEYS = ["health_score", "health_label", "memory_capacity_pct", "governance_label", "last_update_ago"]
CHAT_KEYS = ["goal", "belief", "identity"]


def fetch(path: str) -> tuple[int, dict | list | str]:
    req = urllib.request.Request(BASE + path, method="GET")
    with urllib.request.urlopen(req, timeout=12) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(body)
        except json.JSONDecodeError:
            return resp.status, body


def main() -> int:
    failures: list[str] = []
    print(f"CNexus FE-BE integration check @ {BASE}\n")

    for method, path, required in CHECKS:
        label = f"{method} {path}"
        try:
            status, data = fetch(path)
            if status != 200:
                failures.append(f"{label}: HTTP {status}")
                print(f"FAIL {label}: HTTP {status}")
                continue
            if isinstance(data, dict):
                missing = [k for k in required if k not in data]
                if missing:
                    failures.append(f"{label}: missing keys {missing}")
                    print(f"FAIL {label}: missing {missing}")
                else:
                    extra = ""
                    if path == "/api/status" and "memory_items" in data:
                        items = data.get("memory_items") or []
                        terms = sum(1 for i in items if i.get("tag") == "term")
                        extra = f" | items={len(items)} terms={terms}"
                    print(f"OK   {label}{extra}")
            else:
                print(f"OK   {label} (non-json)")
        except urllib.error.HTTPError as e:
            failures.append(f"{label}: HTTP {e.code}")
            print(f"FAIL {label}: HTTP {e.code}")
        except Exception as e:
            failures.append(f"{label}: {e}")
            print(f"FAIL {label}: {e}")

    # Deep contract for /api/status (MindOverview adapter)
    print("\n--- MindOverview adapter contract (/api/status) ---")
    try:
        _, status = fetch("/api/status")
        if not isinstance(status, dict):
            failures.append("status: not object")
        else:
            cards = status.get("cards") or {}
            feeds = status.get("feeds") or {}
            system = status.get("system") or {}
            chat = status.get("chat_context") or {}
            emotion = status.get("emotion") or {}

            for k in CARD_KEYS:
                if k not in cards:
                    failures.append(f"cards.{k} missing")
            for k in FEED_KEYS:
                if k not in feeds:
                    failures.append(f"feeds.{k} missing")
            for k in SYSTEM_KEYS:
                if k not in system:
                    failures.append(f"system.{k} missing")
            for k in CHAT_KEYS:
                if not chat.get(k):
                    failures.append(f"chat_context.{k} empty/missing")

            # Frontend normalizeEmotion expects valence OR val
            if "arousal" not in emotion:
                failures.append("emotion.arousal missing")
            if "val" not in emotion and "valence" not in emotion:
                failures.append("emotion.val/valence missing")

            items = status.get("memory_items") or []
            if not items:
                failures.append("memory_items empty")
            else:
                sample = items[0]
                for fk in ("id", "title", "tag"):
                    if fk not in sample:
                        failures.append(f"memory_items[0].{fk} missing")

            if failures:
                for f in failures:
                    if f.startswith(("cards", "feeds", "system", "chat", "emotion", "memory")):
                        print(f"FAIL {f}")
            else:
                print("OK   cards/feeds/system/chat_context/memory_items shape")
                print(f"OK   emotion keys: {list(emotion.keys())}")
                terms = [i for i in items if i.get("tag") == "term"]
                print(f"OK   memory_items={len(items)} term_nodes={len(terms)}")
    except Exception as e:
        failures.append(f"contract check: {e}")
        print(f"FAIL contract check: {e}")

  # Stage endpoint (upload pipeline)
    print("\n--- Upload pipeline ---")
    try:
        req = urllib.request.Request(
            BASE + "/api/ingest/documents/stage",
            data=json.dumps({"files": []}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            print(f"OK   POST /api/ingest/documents/stage HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        # 400 for empty files is expected — route exists
        if e.code in (400, 422):
            print(f"OK   POST /api/ingest/documents/stage reachable (HTTP {e.code} expected for empty)")
        else:
            failures.append(f"stage: HTTP {e.code}")
            print(f"FAIL POST /api/ingest/documents/stage HTTP {e.code}")
    except Exception as e:
        failures.append(f"stage: {e}")
        print(f"FAIL POST /api/ingest/documents/stage: {e}")

    print("\n=== Summary ===")
    if failures:
        print(f"FAILED ({len(failures)} issues)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
