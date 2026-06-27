"""Share-memory registry ping + local share stats (anonymous install_id)."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

try:
    from core.install_stats import ensure_install_id, stats_url
except ImportError:
    from install_stats import ensure_install_id, stats_url  # type: ignore

SHARE_STATS_FILENAME = "share_stats.json"


def share_stats_enabled() -> bool:
    if str(os.environ.get("CNEXUS_SHARE_STATS_DISABLE") or "").lower() in ("1", "true", "yes"):
        return False
    return bool(stats_url())


def share_stats_file_path(data_dir: str) -> str:
    return os.path.join(str(data_dir or "."), SHARE_STATS_FILENAME)


def load_share_record(data_dir: str) -> Dict[str, Any]:
    path = share_stats_file_path(data_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_share_record(data_dir: str, record: Dict[str, Any]) -> None:
    path = share_stats_file_path(data_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def share_endpoint(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/v1/share"):
        return base
    return f"{base}/v1/share"


def summary_endpoint(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/v1/stats/summary"):
        return base
    return f"{base}/v1/stats/summary"


def build_share_payload(
    data_dir: str,
    *,
    graph_id: str,
    block_count: int,
    version: str = "2.4.0",
    edition: str = "personal",
) -> Dict[str, Any]:
    return {
        "event": "share",
        "install_id": ensure_install_id(data_dir),
        "graph_id": str(graph_id or ""),
        "block_count": int(block_count or 0),
        "version": str(version or "2.4.0"),
        "edition": str(edition or "personal"),
        "ts": int(time.time()),
    }


def send_share_ping(url: str, payload: Dict[str, Any], *, timeout: float = 8.0) -> Dict[str, Any]:
    endpoint = share_endpoint(url)
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


def record_local_share(
    data_dir: str,
    *,
    graph_id: str,
    block_count: int,
    commit_id: str = "",
    root_hash: str = "",
) -> Dict[str, Any]:
    record = load_share_record(data_dir)
    now = time.time()
    record.update(
        {
            "graph_id": str(graph_id or ""),
            "block_count": int(block_count or 0),
            "commit_id": str(commit_id or ""),
            "root_hash": str(root_hash or ""),
            "last_shared_at": now,
            "share_count": int(record.get("share_count") or 0) + 1,
        }
    )
    save_share_record(data_dir, record)
    return record


def try_register_share(
    data_dir: str,
    *,
    graph_id: str,
    block_count: int,
    commit_id: str = "",
    root_hash: str = "",
    version: str = "2.4.0",
    edition: str = "personal",
) -> Dict[str, Any]:
    local = record_local_share(
        data_dir,
        graph_id=graph_id,
        block_count=block_count,
        commit_id=commit_id,
        root_hash=root_hash,
    )
    if not share_stats_enabled():
        return {"ok": True, "skipped": "stats_url_unconfigured", "local": local}

    url = stats_url()
    payload = build_share_payload(
        data_dir,
        graph_id=graph_id,
        block_count=block_count,
        version=version,
        edition=edition,
    )
    result = send_share_ping(url, payload)
    record = load_share_record(data_dir)
    if result.get("ok"):
        record["last_registry_ping_at"] = time.time()
        record["last_registry_error"] = None
    else:
        record["last_registry_error"] = str(result.get("error") or "ping_failed")
    save_share_record(data_dir, record)
    return {"ok": bool(result.get("ok")), "local": local, "registry": result}


def fetch_remote_summary(url: str = "", *, timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    base = str(url or stats_url()).strip()
    endpoint = summary_endpoint(base)
    if not endpoint:
        return None
    req = urlrequest.Request(endpoint, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw.strip() else {}
            return data if isinstance(data, dict) else None
    except (urlerror.URLError, urlerror.HTTPError, TimeoutError, OSError, ValueError):
        return None


def public_status(
    data_dir: str,
    *,
    sharing_enabled: bool = True,
    version: str = "2.4.0",
    edition: str = "personal",
    fetch_remote: bool = False,
) -> Dict[str, Any]:
    record = load_share_record(data_dir)
    remote = fetch_remote_summary() if fetch_remote and stats_url() else None
    return {
        "ok": True,
        "sharing_enabled": bool(sharing_enabled),
        "stats_url_set": bool(stats_url()),
        "graph_id": record.get("graph_id"),
        "block_count": record.get("block_count", 0),
        "share_count": record.get("share_count", 0),
        "last_shared_at": record.get("last_shared_at"),
        "last_registry_ping_at": record.get("last_registry_ping_at"),
        "last_registry_error": record.get("last_registry_error"),
        "version": version,
        "edition": edition,
        "registry": remote or {},
    }
