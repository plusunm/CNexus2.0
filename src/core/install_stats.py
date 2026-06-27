"""Anonymous first-install ping — opt-in, no memory content, once per install_id."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

INSTALL_STATS_FILENAME = "install_stats.json"
DEFAULT_VERSION = "2.4.0"
DEFAULT_EDITION = "personal"


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).lower() not in ("0", "false", "no", "")


def stats_file_path(data_dir: str) -> str:
    return os.path.join(str(data_dir or "."), INSTALL_STATS_FILENAME)


def load_record(data_dir: str) -> Dict[str, Any]:
    path = stats_file_path(data_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_record(data_dir: str, record: Dict[str, Any]) -> None:
    path = stats_file_path(data_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def ensure_install_id(data_dir: str) -> str:
    record = load_record(data_dir)
    install_id = str(record.get("install_id") or "").strip()
    if not install_id:
        install_id = str(uuid.uuid4())
        record["install_id"] = install_id
        record.setdefault("created_at", time.time())
        save_record(data_dir, record)
    return install_id


def stats_url() -> str:
    return str(os.environ.get("CNEXUS_STATS_URL") or "").strip().rstrip("/")


def opt_in_enabled(record: Optional[Dict[str, Any]] = None, *, data_dir: str = "") -> bool:
    if _env_truthy("CNEXUS_STATS_DISABLE", False):
        return False
    if not stats_url():
        return False
    row = record if record is not None else load_record(data_dir)
    env_opt = str(os.environ.get("CNEXUS_STATS_OPT_IN") or "").strip().lower()
    if env_opt in ("1", "true", "yes"):
        return True
    if env_opt in ("0", "false", "no"):
        return False
    return bool(row.get("opt_in"))


def install_endpoint(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/v1/install") or base.endswith("/install"):
        return base
    return f"{base}/v1/install"


def build_payload(
    data_dir: str,
    *,
    version: str = DEFAULT_VERSION,
    edition: str = DEFAULT_EDITION,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event": "install",
        "install_id": ensure_install_id(data_dir),
        "version": str(version or DEFAULT_VERSION),
        "edition": str(edition or DEFAULT_EDITION),
        "platform": str(platform or sys.platform),
        "ts": int(time.time()),
    }


def send_install_ping(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: float = 8.0,
) -> Dict[str, Any]:
    endpoint = install_endpoint(url)
    if not endpoint:
        return {"ok": False, "error": "missing_stats_url"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw[:200]}
            return {"ok": 200 <= resp.status < 300, "status": resp.status, "response": parsed}
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        return {"ok": False, "error": f"http_{exc.code}", "detail": detail}
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def try_send_first_ping(
    data_dir: str,
    *,
    version: str = DEFAULT_VERSION,
    edition: str = DEFAULT_EDITION,
) -> Dict[str, Any]:
    record = load_record(data_dir)
    if record.get("first_ping_sent_at"):
        return {"ok": True, "skipped": "already_sent", "install_id": record.get("install_id")}
    if not opt_in_enabled(record):
        return {"ok": True, "skipped": "opt_in_disabled"}

    url = stats_url()
    payload = build_payload(data_dir, version=version, edition=edition)
    result = send_install_ping(url, payload)
    if result.get("ok"):
        record["first_ping_sent_at"] = time.time()
        record["last_ping_error"] = None
        save_record(data_dir, record)
        return {"ok": True, "sent": True, "install_id": payload["install_id"], "endpoint": install_endpoint(url)}
    record["last_ping_error"] = str(result.get("error") or "ping_failed")
    save_record(data_dir, record)
    return {"ok": False, "error": record["last_ping_error"], "install_id": payload.get("install_id")}


def schedule_first_ping(
    data_dir: str,
    *,
    version: str = DEFAULT_VERSION,
    edition: str = DEFAULT_EDITION,
) -> None:
    """Fire-and-forget background ping (startup hook)."""

    def _run() -> None:
        try:
            try_send_first_ping(data_dir, version=version, edition=edition)
        except Exception as exc:
            try:
                record = load_record(data_dir)
                record["last_ping_error"] = str(exc)
                save_record(data_dir, record)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True, name="cnexus-install-stats").start()


def public_status(
    data_dir: str,
    *,
    version: str = DEFAULT_VERSION,
    edition: str = DEFAULT_EDITION,
) -> Dict[str, Any]:
    record = load_record(data_dir)
    enabled = opt_in_enabled(record)
    install_id = str(record.get("install_id") or "")
    return {
        "ok": True,
        "configured": bool(stats_url()),
        "stats_url_set": bool(stats_url()),
        "opt_in": enabled,
        "opt_in_ui": bool(record.get("opt_in")),
        "opt_in_env": str(os.environ.get("CNEXUS_STATS_OPT_IN") or ""),
        "install_id": install_id if enabled else None,
        "install_id_short": (
            f"{install_id[:8]}…" if enabled and len(install_id) > 10 else (install_id if enabled else None)
        ),
        "first_ping_sent": bool(record.get("first_ping_sent_at")),
        "first_ping_sent_at": record.get("first_ping_sent_at"),
        "last_ping_error": record.get("last_ping_error"),
        "version": str(version or DEFAULT_VERSION),
        "edition": str(edition or DEFAULT_EDITION),
    }


def set_opt_in(
    data_dir: str,
    enabled: bool,
    *,
    version: str = DEFAULT_VERSION,
    edition: str = DEFAULT_EDITION,
) -> Dict[str, Any]:
    record = load_record(data_dir)
    ensure_install_id(data_dir)
    record = load_record(data_dir)
    record["opt_in"] = bool(enabled)
    save_record(data_dir, record)
    if not enabled:
        return {"ok": True, "opt_in": False}
    if not stats_url():
        return {"ok": False, "error": "CNEXUS_STATS_URL not configured"}
    ping = try_send_first_ping(data_dir, version=version, edition=edition)
    status = public_status(data_dir, version=version, edition=edition)
    return {"ok": ping.get("ok", False), "opt_in": True, "ping": ping, **status}
