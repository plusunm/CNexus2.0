"""Check GitHub Releases for a newer CNexus version — cached, opt-out via env."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest

UPDATE_CACHE_FILENAME = "update_check_cache.json"
DEFAULT_REPO = "plusunm/CNexus2.0"
DEFAULT_VERSION = "2.4.0"
DEFAULT_CACHE_HOURS = 6.0


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).lower() not in ("0", "false", "no", "")


def cache_file_path(data_dir: str) -> str:
    return os.path.join(str(data_dir or "."), UPDATE_CACHE_FILENAME)


def github_repo() -> str:
    return str(os.environ.get("CNEXUS_GITHUB_REPO") or DEFAULT_REPO).strip().strip("/")


def update_check_enabled() -> bool:
    return _env_truthy("CNEXUS_UPDATE_CHECK", True)


def cache_ttl_seconds() -> float:
    raw = os.environ.get("CNEXUS_UPDATE_CHECK_INTERVAL_HOURS")
    try:
        hours = float(raw) if raw is not None else DEFAULT_CACHE_HOURS
    except (TypeError, ValueError):
        hours = DEFAULT_CACHE_HOURS
    return max(0.25, hours) * 3600.0


def normalize_version(raw: str) -> Tuple[int, ...]:
    text = str(raw or "").strip()
    if text.lower().startswith("cnexus"):
        text = re.sub(r"^cnexus[\s\-_]*", "", text, flags=re.I)
    text = text.lstrip("vV")
    parts: list[int] = []
    for segment in text.split("."):
        digits = ""
        for ch in segment:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def compare_versions(current: str, latest: str) -> int:
    """Return -1 if current < latest, 0 if equal, 1 if current > latest."""
    a = normalize_version(current)
    b = normalize_version(latest)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def load_cache(data_dir: str) -> Dict[str, Any]:
    path = cache_file_path(data_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_cache(data_dir: str, record: Dict[str, Any]) -> None:
    path = cache_file_path(data_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _github_latest_url(repo: str) -> str:
    slug = str(repo or DEFAULT_REPO).strip().strip("/")
    return f"https://api.github.com/repos/{slug}/releases/latest"


def fetch_github_latest(
    repo: Optional[str] = None,
    *,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    slug = str(repo or github_repo()).strip().strip("/")
    if not slug or "/" not in slug:
        return {"ok": False, "error": "invalid_github_repo", "repo": slug}

    req = urlrequest.Request(
        _github_latest_url(slug),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "CNexus-Update-Check",
        },
        method="GET",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw.strip() else {}
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:240]
        return {"ok": False, "error": f"http_{exc.code}", "detail": detail, "repo": slug}
    except (urlerror.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "repo": slug}

    if not isinstance(payload, dict):
        return {"ok": False, "error": "invalid_github_payload", "repo": slug}

    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        return {"ok": False, "error": "missing_tag_name", "repo": slug}

    body = str(payload.get("body") or "").strip()
    if len(body) > 480:
        body = body[:477].rstrip() + "…"

    return {
        "ok": True,
        "repo": slug,
        "latest_version": tag.lstrip("vV"),
        "tag_name": tag,
        "release_name": str(payload.get("name") or tag),
        "release_url": str(payload.get("html_url") or f"https://github.com/{slug}/releases/latest"),
        "published_at": payload.get("published_at"),
        "release_notes": body,
        "prerelease": bool(payload.get("prerelease")),
        "draft": bool(payload.get("draft")),
    }


def _cache_fresh(record: Dict[str, Any], current_version: str) -> bool:
    checked_at = float(record.get("checked_at") or 0)
    if not checked_at:
        return False
    if str(record.get("current_version") or "") != str(current_version or ""):
        return False
    return (time.time() - checked_at) < cache_ttl_seconds()


def check_update(
    data_dir: str,
    *,
    current_version: str = DEFAULT_VERSION,
    force: bool = False,
) -> Dict[str, Any]:
    current = str(current_version or DEFAULT_VERSION)
    enabled = update_check_enabled()
    base: Dict[str, Any] = {
        "ok": True,
        "enabled": enabled,
        "current_version": current,
        "update_available": False,
        "source": "github",
        "repo": github_repo(),
        "checked_at": time.time(),
    }

    if not enabled:
        base["skipped"] = "disabled"
        return base

    cached = load_cache(data_dir)
    if not force and _cache_fresh(cached, current):
        return {**cached, "ok": True, "cached": True, "enabled": True}

    remote = fetch_github_latest()
    if not remote.get("ok"):
        stale = dict(cached)
        stale.update(
            {
                "ok": True,
                "enabled": True,
                "current_version": current,
                "update_available": bool(cached.get("update_available")),
                "cached": True,
                "stale": True,
                "error": str(remote.get("error") or "github_fetch_failed"),
                "checked_at": float(cached.get("checked_at") or time.time()),
            }
        )
        if stale.get("latest_version"):
            return stale
        return {
            **base,
            "error": str(remote.get("error") or "github_fetch_failed"),
            "update_available": False,
        }

    latest = str(remote.get("latest_version") or "")
    update_available = compare_versions(current, latest) < 0
    record = {
        **base,
        "latest_version": latest,
        "tag_name": remote.get("tag_name"),
        "release_name": remote.get("release_name"),
        "release_url": remote.get("release_url"),
        "published_at": remote.get("published_at"),
        "release_notes": remote.get("release_notes"),
        "update_available": update_available,
        "error": None,
        "cached": False,
    }
    save_cache(data_dir, record)
    return record


def schedule_startup_check(
    data_dir: str,
    *,
    current_version: str = DEFAULT_VERSION,
) -> None:
    """Warm GitHub release cache in the background on gateway boot."""

    def _run() -> None:
        try:
            check_update(data_dir, current_version=current_version, force=False)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True, name="cnexus-update-check").start()


def public_status(
    data_dir: str,
    *,
    current_version: str = DEFAULT_VERSION,
    force: bool = False,
) -> Dict[str, Any]:
    return check_update(data_dir, current_version=current_version, force=force)
