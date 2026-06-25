"""Benchmark converse stream latency breakdown."""
from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:7864"


def bench(label: str, payload: dict) -> None:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/api/converse/stream",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    )
    t0 = time.perf_counter()
    first_meta = None
    first_token = None
    done = None
    events: list[str] = []
    with urllib.request.urlopen(req, timeout=180) as resp:
        buf = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n\n" in buf:
                block, buf = buf.split(b"\n\n", 1)
                text = block.decode("utf-8", errors="replace")
                event = "message"
                data = ""
                for line in text.split("\n"):
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        data = line[5:].strip()
                if not data:
                    continue
                now = time.perf_counter()
                events.append(event)
                if event == "meta" and first_meta is None:
                    first_meta = now
                if event == "token" and first_token is None:
                    first_token = now
                if event == "done":
                    done = now
                    try:
                        done_payload = json.loads(data)
                    except json.JSONDecodeError:
                        done_payload = {}
                    server = done_payload.get("latency_ms") or {}
                    print(
                        f"{label}:"
                        f" meta={round((first_meta - t0) * 1000) if first_meta else '?'}ms"
                        f" ttft={round((first_token - t0) * 1000) if first_token else '?'}ms"
                        f" done={round((done - t0) * 1000) if done else '?'}ms"
                        f" | server prepare={server.get('prepare')} llm={server.get('llm')}"
                        f" post={server.get('post')} ttft={server.get('ttft')} total={server.get('total')}"
                        f" | llm_source={done_payload.get('llm_source')} model={done_payload.get('model_name')}"
                        f" activation={done_payload.get('activation_injected')}"
                    )
                    return
    print(f"{label}: incomplete stream events={events[:12]}")


def main() -> None:
    try:
        urllib.request.urlopen(f"{BASE}/api/status", timeout=5)
    except Exception as exc:
        print(f"gateway offline: {exc}")
        return

    for mode in ("raw", "fast", "deep"):
        bench(
            mode,
            {
                "text": "你好，用一句话介绍你自己。",
                "stream": True,
                "converse_mode": mode,
                "thinking_mode": "precision",
            },
        )


if __name__ == "__main__":
    main()
