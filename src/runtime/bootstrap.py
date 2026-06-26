"""CNexus BOOT sequence — Constitution → Policy → (Memory layers follow separately)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Optional

from .compiler import compile_if_needed, runtime_source_roots
from .context import build_runtime_system_prompt
from .types import BootPhase, CompiledRuntime


class RuntimeBootstrap:
    """Load compiled Runtime — Constitution is NOT Memory."""

    def __init__(self, app_root: str, *, data_dir: Optional[str] = None):
        self._app_root = app_root
        self._data_dir = data_dir or os.path.join(app_root, "data", "runtime")

    @property
    def data_dir(self) -> str:
        return self._data_dir

    def boot(self, *, force_recompile: bool = False) -> CompiledRuntime:
        result = compile_if_needed(self._app_root, self._data_dir, force=force_recompile)
        compiled: CompiledRuntime = result["compiled"]
        compiled.boot_phase = BootPhase.CONVERSATION_READY
        return compiled

    def system_prompt(self, compiled: Optional[CompiledRuntime] = None) -> str:
        bundle = compiled or read_active(self._app_root, self._data_dir)
        if bundle is None:
            return ""
        return build_runtime_system_prompt(bundle)

    def status(self, compiled: Optional[CompiledRuntime] = None) -> Dict[str, Any]:
        bundle = compiled or read_active(self._app_root, self._data_dir)
        if bundle is None:
            constitution_dir, policy_dir = runtime_source_roots(self._app_root)
            return {
                "ok": False,
                "boot_phase": BootPhase.BOOT.value,
                "error": "runtime_not_compiled",
                "constitution_dir": constitution_dir,
                "policy_dir": policy_dir,
            }
        out = bundle.status_dict()
        out["ok"] = True
        out["system_prompt_chars"] = len(build_runtime_system_prompt(bundle))
        out["constitution_dir"], out["policy_dir"] = runtime_source_roots(self._app_root)
        out["bundle_path"] = os.path.join(self._data_dir, "constitution.bin")
        return out


def read_active(app_root: str, data_dir: str) -> Optional[CompiledRuntime]:
    from .compiler import read_compiled_bundle

    return read_compiled_bundle(data_dir)


def boot_runtime(
    app_root: str,
    *,
    data_dir: Optional[str] = None,
    force_recompile: bool = False,
    identity_manager: Any = None,
) -> Dict[str, Any]:
    """One-shot boot used by app_v2.main()."""
    from .compiler import compile_if_needed

    boot = RuntimeBootstrap(app_root, data_dir=data_dir)
    compile_meta = compile_if_needed(
        app_root,
        boot.data_dir,
        force=force_recompile,
        identity_manager=identity_manager,
    )
    compiled: CompiledRuntime = compile_meta["compiled"]
    compiled.boot_phase = BootPhase.CONVERSATION_READY
    status = boot.status(compiled)
    status["recompiled"] = bool(compile_meta.get("recompiled"))
    status["signature_verified"] = bool(compile_meta.get("signature_verified"))
    status["ed25519_signed"] = bool(compile_meta.get("ed25519_signed"))
    status["tampered_replaced"] = bool(compile_meta.get("tampered_replaced"))
    system_prompt = boot.system_prompt(compiled)
    return {
        "compiled": compiled,
        "status": status,
        "system_prompt": system_prompt,
    }
