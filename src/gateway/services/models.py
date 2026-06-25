"""Model registry CRUD, connectivity tests, and Ollama registry sync."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import request as urlrequest

from ..state import EngineStateManager

SchedulePersistFn = Callable[[], None]


class ModelConfigService:
    """Personal-edition model configuration — no HTTP, no app_v2 imports."""

    def __init__(
        self,
        state: EngineStateManager,
        *,
        schedule_persist: SchedulePersistFn,
        ollama_host: str = "127.0.0.1:11434",
        ollama_registry_ttl: float = 30.0,
    ):
        self._state = state
        self._schedule_persist = schedule_persist
        self._ollama_host = ollama_host
        self._ollama_registry_ttl = ollama_registry_ttl
        self._ollama_cache: Dict[str, Any] = {"at": 0.0, "status": None}
        self._ollama_lock = threading.Lock()

    @staticmethod
    def default_registry(ollama_host: str = "127.0.0.1:11434") -> Dict[str, Dict[str, Any]]:
        return {
            "cnexus-local": {
                "id": "cnexus-local",
                "name": "CNexus 2.0 Local",
                "provider": "cnexus",
                "base_url": "",
                "model": "cognitive-kernel",
                "api_key": "",
                "api_key_set": True,
                "is_default": True,
                "enabled": True,
            },
            "ollama-local": {
                "id": "ollama-local",
                "name": "Ollama 本地",
                "provider": "ollama",
                "base_url": f"http://{ollama_host}",
                "model": "llama3.2",
                "api_key": "",
                "api_key_set": True,
                "is_default": False,
                "enabled": False,
            },
            "deepseek-chat": {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "provider": "openai_compatible",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-flash",
                "api_key": "",
                "api_key_set": False,
                "is_default": False,
                "enabled": False,
            },
            "openai-default": {
                "id": "openai-default",
                "name": "OpenAI",
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "api_key": "",
                "api_key_set": False,
                "is_default": False,
                "enabled": False,
            },
        }

    @staticmethod
    def to_public(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row.get("name", row["id"]),
            "provider": row.get("provider", "openai_compatible"),
            "base_url": row.get("base_url", ""),
            "model": row.get("model", ""),
            "api_key_set": bool(row.get("api_key_set") or (row.get("api_key") or "").strip()),
            "is_default": bool(row.get("is_default")),
            "enabled": bool(row.get("enabled", True)),
        }

    def ollama_base_url(self) -> str:
        row = self._state.get_model_row("ollama-local") or {}
        return (row.get("base_url") or f"http://{self._ollama_host}").rstrip("/")

    def active_model_id(self) -> str:
        def pick(reg: Dict[str, Dict[str, Any]]) -> str:
            for row in reg.values():
                if row.get("is_default") and row.get("enabled", True):
                    return row["id"]
            for row in reg.values():
                if row.get("enabled", True):
                    return row["id"]
            return "cnexus-local"

        return self._state.mutate_model_registry(pick)

    def resolve_model_row(self, model_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Resolve a registry row by id, seeding built-in defaults when missing."""
        mid = model_id or self.active_model_id()
        defaults = self.default_registry(self._ollama_host)

        def resolve(reg: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            row = reg.get(mid)
            if not row and mid in defaults:
                row = dict(defaults[mid])
                reg[mid] = row
            return row

        return self._state.mutate_model_registry(resolve)

    @staticmethod
    def _row_usable_for_chat(row: Dict[str, Any]) -> bool:
        if not row or not row.get("enabled", True):
            return False
        provider = str(row.get("provider") or "")
        if provider in ("cnexus", ""):
            return False
        if provider == "ollama":
            return True
        return bool(str(row.get("api_key") or "").strip())

    def _best_external_chat_row(self, reg: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for row in reg.values():
            if row.get("is_default") and self._row_usable_for_chat(row):
                return row
        ollama = reg.get("ollama-local")
        if self._row_usable_for_chat(ollama or {}):
            return ollama
        for row in reg.values():
            if self._row_usable_for_chat(row):
                return row
        return None

    def resolve_model_row_for_chat(self, model_id: Optional[str] = None, *, force_sync: bool = False) -> Optional[Dict[str, Any]]:
        """Resolve active/chat model row, refreshing Ollama registry when needed."""
        row = self.resolve_model_row(model_id)
        if row and row.get("provider") == "ollama" and row.get("enabled", True):
            self.sync_ollama_registry(force=force_sync)
            row = self.resolve_model_row(model_id)

        if row and str(row.get("provider") or "") in ("cnexus", ""):
            def pick_alt(reg: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
                alt = self._best_external_chat_row(reg)
                return alt if alt is not None else row

            alt = self._state.mutate_model_registry(pick_alt)
            if alt is not None and alt.get("id") != row.get("id"):
                row = alt
        return row

    def list_models(self) -> Dict[str, List[Dict[str, Any]]]:
        self.sync_ollama_registry()
        rows = self._state.mutate_model_registry(
            lambda reg: [self.to_public(row) for row in reg.values()],
        )
        rows.sort(key=lambda r: (not r["is_default"], r["name"]))
        return {"models": rows}

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        row = self._state.get_model_row(model_id)
        return self.to_public(row) if row else None

    def upsert(
        self,
        model_id: str,
        body: Dict[str, Any],
        *,
        create: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        defaults = self.default_registry(self._ollama_host)

        def apply(reg: Dict[str, Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
            if create and model_id in reg:
                return None, "model_exists"
            if not create and model_id not in reg:
                if model_id in defaults:
                    reg[model_id] = dict(defaults[model_id])
                else:
                    return None, "not_found"

            row = dict(reg.get(model_id, {"id": model_id}))
            for key in ("name", "provider", "base_url", "model"):
                if key in body and body[key] is not None:
                    row[key] = body[key]
            if "api_key" in body:
                row["api_key"] = str(body.get("api_key") or "")
                row["api_key_set"] = bool(str(body.get("api_key") or "").strip()) or row.get("provider") == "ollama"
            if "enabled" in body:
                row["enabled"] = bool(body["enabled"])
            if "is_default" in body and body["is_default"]:
                for other in reg.values():
                    other["is_default"] = False
                row["is_default"] = True
            elif "is_default" in body:
                row["is_default"] = bool(body["is_default"])

            if row.get("provider") == "ollama":
                row["api_key_set"] = True
            reg[model_id] = row
            return self.to_public(row), None

        result = self._state.mutate_model_registry(apply)
        if result[0] is not None:
            self._schedule_persist()
        return result

    def create(self, body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        preset_id = (body.get("presetId") or body.get("preset_id") or "").strip()
        if preset_id:
            row, err = self.upsert(preset_id, body, create=False)
            if err == "not_found":
                row, err = self.upsert(preset_id, {**body, "id": preset_id}, create=True)
            return row, err

        model_id = f"custom-{int(time.time() * 1000)}"

        def seed(reg: Dict[str, Dict[str, Any]]) -> None:
            reg[model_id] = {
                "id": model_id,
                "name": body.get("name") or "Custom Model",
                "provider": body.get("provider") or "openai_compatible",
                "base_url": body.get("base_url") or "",
                "model": body.get("model") or "",
                "api_key": body.get("api_key") or "",
                "api_key_set": bool((body.get("api_key") or "").strip()),
                "is_default": bool(body.get("is_default")),
                "enabled": bool(body.get("enabled", True)),
            }

        self._state.mutate_model_registry(seed)
        return self.upsert(model_id, body, create=False)

    def test(self, model_id: str, *, quick: bool = False) -> Dict[str, Any]:
        row = self.resolve_model_row(model_id)
        if not row:
            return {"success": False, "detail": f"model not found: {model_id}"}

        provider = row.get("provider", "")
        if provider == "cnexus":
            return {"success": True, "detail": "CNexus 内置认知内核可用"}

        if provider == "ollama":
            host = (row.get("base_url") or f"http://{self._ollama_host}").rstrip("/")
            try:
                installed = self.list_ollama_chat_models(host)
                target = row.get("model") or ""
                resolved = self.resolve_ollama_model_name(target, installed) if installed else target
                if resolved and resolved != target:
                    self._state.mutate_model_registry(
                        lambda reg: reg[model_id].update({"model": resolved}) or None,
                    )
                    self._schedule_persist()
                if quick:
                    if installed and resolved:
                        return {"success": True, "detail": f"Ollama 已连接 · 模型 {resolved}（快速检测）"}
                    if installed:
                        return {
                            "success": True,
                            "detail": f"Ollama 已连接，可用模型 {len(installed)} 个（快速检测）",
                        }
                    return {"success": False, "detail": "Ollama 未运行或未找到可对话模型"}
                if installed and resolved:
                    probe = json.dumps(
                        {
                            "model": resolved,
                            "messages": [{"role": "user", "content": "ping"}],
                            "stream": False,
                        },
                    ).encode("utf-8")
                    req = urlrequest.Request(
                        f"{host}/api/chat",
                        data=probe,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urlrequest.urlopen(req, timeout=30) as resp:
                        json.loads(resp.read().decode("utf-8", errors="replace"))
                    return {"success": True, "detail": f"Ollama 已连接 · 模型 {resolved}"}
                if not installed:
                    return {"success": False, "detail": "Ollama 已运行但未找到可对话模型，请先 ollama pull"}
                return {"success": True, "detail": f"Ollama 已连接，可用模型 {len(installed)} 个"}
            except Exception as exc:
                return {"success": False, "detail": f"Ollama 不可达: {exc}"}

        if not (row.get("api_key") or "").strip() and provider != "ollama":
            return {"success": False, "detail": "未配置 API Key"}
        return {"success": True, "detail": "API Key 已保存（个人版跳过云端连通性实测）"}

    def list_ollama_chat_models(self, base_url: Optional[str] = None) -> List[str]:
        base = (base_url or self.ollama_base_url()).rstrip("/")
        try:
            req = urlrequest.Request(f"{base}/api/tags", method="GET")
            with urlrequest.urlopen(req, timeout=1) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return []
        out: List[str] = []
        for item in payload.get("models") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            caps = item.get("capabilities") or []
            lower = name.lower()
            if caps and not any(c in caps for c in ("completion", "chat", "tools")):
                continue
            if "embed" in lower and not any(c in caps for c in ("completion", "chat", "tools")):
                continue
            out.append(name)
        return out

    @staticmethod
    def resolve_ollama_model_name(preferred: str, installed: List[str]) -> str:
        preferred = str(preferred or "").strip()
        if not installed:
            return preferred or "llama3.2"
        if preferred in installed:
            return preferred
        for name in installed:
            base = name.split(":")[0]
            if base == preferred or name.startswith(preferred + ":"):
                return name
        return installed[0]

    def probe_ollama_running(self) -> bool:
        try:
            req = urlrequest.Request(f"{self.ollama_base_url()}/api/tags", method="GET")
            with urlrequest.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except Exception:
            return False

    def sync_ollama_registry(self, force: bool = False) -> None:
        """Update ollama-local row from a lightweight probe (no full chat ping)."""
        now = time.time()
        with self._ollama_lock:
            cached = self._ollama_cache.get("status")
            if (
                not force
                and cached is not None
                and now - float(self._ollama_cache.get("at") or 0.0) < self._ollama_registry_ttl
            ):
                return

        def apply(reg: Dict[str, Dict[str, Any]]) -> None:
            row = reg.get("ollama-local")
            if not row:
                return
            base = self.ollama_base_url()
            installed = self.list_ollama_chat_models(base)
            running = bool(installed) or self.probe_ollama_running()

            if running and installed:
                preferred = str(row.get("model") or "llama3.2")
                row["model"] = self.resolve_ollama_model_name(preferred, installed)
                row["enabled"] = True
                row["api_key_set"] = True
                cloud_ready = any(
                    other.get("id") not in ("ollama-local", "cnexus-local")
                    and other.get("enabled")
                    and other.get("provider") not in ("cnexus", "ollama", "")
                    and (other.get("api_key_set") or bool((other.get("api_key") or "").strip()))
                    for other in reg.values()
                )
                if not cloud_ready:
                    for other in reg.values():
                        other["is_default"] = False
                    row["is_default"] = True
            elif running:
                row["enabled"] = True
                row["api_key_set"] = True
            else:
                row["enabled"] = False
                if row.get("is_default"):
                    row["is_default"] = False
                    local = reg.get("cnexus-local")
                    if local:
                        local["is_default"] = True
            reg["ollama-local"] = row

        self._state.mutate_model_registry(apply)
        with self._ollama_lock:
            self._ollama_cache["at"] = time.time()
            self._ollama_cache["status"] = True
