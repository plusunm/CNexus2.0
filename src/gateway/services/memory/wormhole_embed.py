"""Wormhole embedding backend — local Ollama + optional cloud fallback."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from urllib import request as urlrequest

AppendLogFn = Callable[..., None]
OllamaBaseUrlFn = Callable[[], str]
ProbeOllamaFn = Callable[[], bool]


def _default_ollama_base_url() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host}".rstrip("/")


def _default_probe_ollama(base_url_fn: OllamaBaseUrlFn) -> bool:
    try:
        req = urlrequest.Request(f"{base_url_fn()}/api/tags", method="GET")
        with urlrequest.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


@dataclass(frozen=True)
class WormholeEmbedderHooks:
    append_runtime_log: AppendLogFn = lambda *a, **k: None
    ollama_base_url: OllamaBaseUrlFn = _default_ollama_base_url
    probe_ollama: Optional[ProbeOllamaFn] = None


class WormholeEmbedder:
    """Single-backend embeddings for wormhole cosine resonance."""

    def __init__(self, hooks: Optional[WormholeEmbedderHooks] = None):
        self._hooks = hooks or WormholeEmbedderHooks()
        self._cache: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def backend(self) -> Optional[str]:
        probe = self._hooks.probe_ollama or (lambda: _default_probe_ollama(self._hooks.ollama_base_url))
        if probe() and self._list_ollama_embed_models():
            return "ollama"
        if (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")):
            return "cloud"
        return None

    def embed(self, text: str, backend: Optional[str] = None) -> List[float]:
        text = str(text or "").strip()
        if not text:
            return []
        backend = backend or self.backend()
        if not backend:
            return []
        cached = self._get_cached(text, backend)
        if cached:
            return cached
        if backend == "ollama":
            vector = self._ollama_embedding(text)
        elif backend == "cloud":
            vector = self._cloud_embedding(text)
        else:
            vector = []
        if vector:
            self._cache_vector(text, backend, vector)
        return vector

    def _cache_key(self, text: str, backend: str) -> str:
        return f"{backend}:{text}"

    def _get_cached(self, text: str, backend: str) -> List[float]:
        with self._lock:
            return list(self._cache.get(self._cache_key(text, backend)) or [])

    def _cache_vector(self, text: str, backend: str, vector: List[float]) -> None:
        if not text or not vector:
            return
        with self._lock:
            self._cache[self._cache_key(text, backend)] = list(vector)

    def _list_ollama_embed_models(self) -> List[str]:
        try:
            req = urlrequest.Request(f"{self._hooks.ollama_base_url()}/api/tags", method="GET")
            with urlrequest.urlopen(req, timeout=3) as resp:
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
            if "embed" in caps or "embedding" in caps or "embed" in lower:
                out.append(name)
        return out

    def _resolve_embed_model(self) -> str:
        preferred = os.environ.get("CNEXUS_EMBED_MODEL", "").strip()
        installed = self._list_ollama_embed_models()
        if preferred:
            for name in installed:
                if name == preferred or name.startswith(preferred + ":"):
                    return name
            if "embed" not in preferred.lower():
                return preferred
        if installed:
            return installed[0]
        return preferred or "nomic-embed-text"

    def _ollama_embedding(self, text: str) -> List[float]:
        probe = self._hooks.probe_ollama or (lambda: _default_probe_ollama(self._hooks.ollama_base_url))
        if not probe():
            return []
        model = self._resolve_embed_model()
        url = f"{self._hooks.ollama_base_url()}/api/embeddings"
        body = json.dumps({"model": model, "prompt": text}).encode("utf-8")
        try:
            req = urlrequest.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=5.0) as response:
                res_data = json.loads(response.read().decode("utf-8", errors="replace"))
                vector = res_data.get("embedding") or []
                return list(vector) if vector else []
        except Exception as exc:
            self._hooks.append_runtime_log(f"本地向量降级 · {exc}", category="embed", level="warn")
        return []

    def _cloud_embedding(self, text: str) -> List[float]:
        deepseek_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if deepseek_key:
            url = (os.environ.get("DEEPSEEK_EMBED_URL") or "https://api.deepseek.com/v1/embeddings").rstrip("/")
            model = (os.environ.get("CNEXUS_CLOUD_EMBED_MODEL") or "deepseek-embedding-v2").strip()
            api_key = deepseek_key
            provider = "deepseek"
        elif openai_key:
            url = (os.environ.get("OPENAI_EMBED_URL") or "https://api.openai.com/v1/embeddings").rstrip("/")
            model = (os.environ.get("CNEXUS_CLOUD_EMBED_MODEL") or "text-embedding-3-small").strip()
            api_key = openai_key
            provider = "openai"
        else:
            return []

        body = json.dumps({"model": model, "input": text}).encode("utf-8")
        try:
            req = urlrequest.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=12.0) as response:
                res_data = json.loads(response.read().decode("utf-8", errors="replace"))
                vector = None
                if isinstance(res_data.get("embedding"), list):
                    vector = res_data["embedding"]
                else:
                    rows = res_data.get("data") or []
                    if rows and isinstance(rows[0], dict):
                        vector = rows[0].get("embedding")
                if vector:
                    self._hooks.append_runtime_log(
                        f"云端向量容灾 · provider={provider} dim={len(vector)}",
                        category="embed",
                        level="info",
                    )
                    return list(vector)
        except Exception as exc:
            self._hooks.append_runtime_log(f"云端向量降级 · {exc}", category="embed", level="warn")
        return []
