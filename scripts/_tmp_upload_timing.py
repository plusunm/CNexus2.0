"""Quick upload endpoint timing probe."""
from __future__ import annotations

import time
import urllib.error
import urllib.request
BASE = "http://127.0.0.1:7864"


def probe(label: str, url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: float = 15) -> None:
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET", headers=headers or {})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(400)
            print(f"{label}: {resp.status} in {time.perf_counter() - t0:.3f}s -> {body[:180]!r}")
    except urllib.error.HTTPError as exc:
        err_body = exc.read(400)
        print(f"{label}: HTTP {exc.code} in {time.perf_counter() - t0:.3f}s -> {err_body[:180]!r}")
    except Exception as exc:
        print(f"{label}: ERROR in {time.perf_counter() - t0:.3f}s -> {exc}")


def main() -> None:
    probe("status", f"{BASE}/api/status", timeout=5)

    boundary = "----cnexusprobe"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="t.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "hello upload probe\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    probe("stage", f"{BASE}/api/ingest/documents/stage", data=body, headers=headers)

    body2 = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="t.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "hello upload probe\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="layer"\r\n\r\n'
        "episodic\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="importance"\r\n\r\n'
        "0.7\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    probe("file_upload", f"{BASE}/v1/gateway/file/upload", data=body2, headers=headers)


if __name__ == "__main__":
    main()
