#!/usr/bin/env python3
"""Minimal CNexus install + share stats collector — run on a VPS and point clients at it.

Example:
  python scripts/stats_collect_server.py --port 8787
  set CNEXUS_STATS_URL=http://your-vps:8787
  set CNEXUS_STATS_OPT_IN=1

Stores one line per event in data/stats_installs.jsonl (dedupe by install_id for install events).
Share heartbeats use POST /v1/share (dedupe unique_sharing_clients by install_id).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Set


class StatsStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen_install: Set[str] = set()
        self._seen_share: Set[str] = set()
        self._share_event_count = 0
        self._load_seen()

    def _load_seen(self) -> None:
        if not self.path.is_file():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                event = str(row.get("event") or "install")
                install_id = str(row.get("install_id") or "").strip()
                if event == "install" and install_id:
                    self._seen_install.add(install_id)
                elif event == "share":
                    self._share_event_count += 1
                    if install_id:
                        self._seen_share.add(install_id)
        except (OSError, ValueError):
            pass

    def summary(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "unique_installs": len(self._seen_install),
            "unique_sharing_clients": len(self._seen_share),
            "total_share_events": self._share_event_count,
        }

    def append(self, row: Dict[str, Any]) -> Dict[str, Any]:
        event = str(row.get("event") or "install")
        install_id = str(row.get("install_id") or "").strip()
        if event == "install" and install_id:
            if install_id in self._seen_install:
                return {
                    "ok": True,
                    "duplicate": True,
                    "install_id": install_id,
                    **self.summary(),
                }
            self._seen_install.add(install_id)
        elif event == "share":
            self._share_event_count += 1
            if install_id:
                self._seen_share.add(install_id)
        enriched = {
            **row,
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")
        return {"ok": True, "stored": True, **self.summary()}


def make_handler(store: StatsStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _json(self, code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/") in ("", "/health", "/v1/health"):
                self._json(200, {"service": "cnexus-stats-collector", **store.summary()})
                return
            if self.path.rstrip("/") == "/v1/stats/summary":
                self._json(200, store.summary())
                return
            self._json(404, {"ok": False, "error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.rstrip("/")
            if path not in ("/v1/install", "/install", "/v1/share", "/share"):
                self._json(404, {"ok": False, "error": "not_found"})
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._json(400, {"ok": False, "error": "invalid_json"})
                return
            if not str(payload.get("install_id") or "").strip():
                self._json(400, {"ok": False, "error": "missing_install_id"})
                return
            if path in ("/v1/share", "/share"):
                payload.setdefault("event", "share")
            else:
                payload.setdefault("event", "install")
            result = store.append(payload)
            self._json(200, result)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="CNexus anonymous install + share stats collector")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--out",
        default=os.path.join("data", "stats_installs.jsonl"),
        help="JSONL output path",
    )
    args = parser.parse_args()
    store = StatsStore(Path(args.out))
    summary = store.summary()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print(f"CNexus stats collector on http://{args.host}:{args.port}")
    print(f"  POST /v1/install  -> {Path(args.out).resolve()}")
    print(f"  POST /v1/share    -> share heartbeats")
    print(
        f"  GET  /v1/stats/summary -> "
        f"installs={summary['unique_installs']} sharing={summary['unique_sharing_clients']}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
