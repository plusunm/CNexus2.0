"""Control-plane POST operations — memory, replay, conflict, pruning."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from .conflict_control import ConflictControlService
from .consensus_control import ConsensusControlService
from .memory_control import MemoryControlService
from .pruning_control import PruningControlService
from .reflection_control import ReflectionControlService
from .rem_control import RemControlService
from .replay_control import ReplayControlService
from .shadow_projection import ShadowProjectionService

JsonResponse = Tuple[Any, int]


class ControlPlaneService:
    """Gateway-owned control APIs — zero ControlPlaneHooks."""

    def __init__(
        self,
        shadow: ShadowProjectionService,
        memory: MemoryControlService,
        replay: ReplayControlService,
        reflection: ReflectionControlService,
        rem: RemControlService,
        conflict: ConflictControlService,
        pruning: PruningControlService,
        consensus: ConsensusControlService,
    ):
        self._shadow = shadow
        self._memory = memory
        self._replay = replay
        self._reflection = reflection
        self._rem = rem
        self._conflict = conflict
        self._pruning = pruning
        self._consensus = consensus

    def memory_clear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        keep_models = data.get("keep_models", True)
        if isinstance(keep_models, str):
            keep_models = keep_models.lower() not in ("0", "false", "no")
        return self._memory.clear(keep_models=bool(keep_models))

    def memory_promote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._memory.promote(data)

    def memory_foundation_upgrade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._memory.foundation_upgrade(data)

    def memory_foundation_versions(self, constitution_key: Optional[str] = None) -> Dict[str, Any]:
        return self._memory.foundation_versions(constitution_key=constitution_key)

    def memory_foundation_tree(self, constitution_key: Optional[str] = None) -> Dict[str, Any]:
        return self._memory.foundation_version_tree(constitution_key=constitution_key)

    def memory_constitution_bootstrap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        force = data.get("force", False)
        if isinstance(force, str):
            force = force.lower() in ("1", "true", "yes")
        return self._memory.bootstrap_constitution(force=bool(force))

    def runtime_recompile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        force = data.get("force", False)
        if isinstance(force, str):
            force = force.lower() in ("1", "true", "yes")
        return self._memory.bootstrap_constitution(force=bool(force))

    def runtime_boot_status(self) -> Dict[str, Any]:
        return self._memory.runtime_status()

    def rem_sleep(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._rem.run(data)

    def replay_run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._replay.run(data)

    def reflect_meta(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self._reflection.reflect_meta(data)

    def conflict_resolve(self, data: Dict[str, Any]) -> JsonResponse:
        return self._conflict.resolve(data)

    def conflict_settings(self, data: Dict[str, Any]) -> JsonResponse:
        return self._conflict.update_settings(data)

    def pruning_run(self, data: Dict[str, Any]) -> JsonResponse:
        return self._pruning.run(data)

    def consensus_reputation(self, data: Dict[str, Any]) -> JsonResponse:
        return self._consensus.update_reputation(data)

    def cse_synthesize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        window = int(data.get("window") or 200)
        return self._shadow.cse_synthesize(window)

    def ollama_start(self) -> Dict[str, Any]:
        return self._shadow.ollama_start()

    def ollama_stop(self) -> Dict[str, Any]:
        return self._shadow.ollama_stop()

    @staticmethod
    def read_json_body(http: Any) -> Dict[str, Any]:
        length = int(http.headers.get("Content-Length", 0))
        body = http.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(body) if body else {}
        except Exception:
            return {}

    @staticmethod
    def post_data(http: Any) -> Dict[str, Any]:
        data = http._get_post_data()
        return data if isinstance(data, dict) else {}
