"""Guard script — v2_handler.py is hand-maintained; do not regenerate from app_v2.

Domain route handlers live under src/gateway/routes/:
  system_status, asset, peer, converse, ingest, control, static, models

V2Bindings (see src/gateway/routes/v2_handler.py):
  models_routes, converse_routes, ingest_routes,
  status_routes, asset_routes, peer_routes, control_routes,
  static_routes, auth_gate, put_routes, post_routes

Init order in app_v2.py (end of file):
  memory_graph → memory_rem → activation → memory_recall → negotiation → converse_audit
  → turn_persistence → converse → status (bootstrap) → status_routes
  → auth → control (bootstrap) → projection_register → projection_ingest
  → asset_route (bootstrap) → gateway_intent → control_routes → static → v2_handler

ConverseConfigService + ExternalLlmService use converse_thinking (no conversation_engine hook).
Only global_entropy_int remains as converse/LLM hook — provenance is ProvenancePort on Memory Domain.
Asset stack wired via build_asset_route_services() in asset_route_bootstrap.py.
POST/PUT route lists built via build_post_routes() / build_put_routes() in routes/registry.py.
MemoryRemService owns REM context, deep-sleep cycle, watchdog, and consolidation synthesis (RemConsolidationSynthesizer).
Status stack wired via build_status_services() in status_bootstrap.py.
Control stack wired via build_control_services() in control_bootstrap.py.

PUT dispatch: bindings.put_routes — handlers exposing handle_put_route(path, http)
POST dispatch: bindings.post_routes — callables (handler, path, query) -> HttpRouteResponse | None
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "gateway" / "routes" / "v2_handler.py"

if __name__ == "__main__":
    if not TARGET.is_file():
        print(f"error: missing {TARGET}", file=sys.stderr)
        sys.exit(1)
    print(__doc__.strip())
    print()
    print(f"OK: {TARGET.relative_to(ROOT)} is maintained manually ({TARGET.stat().st_size} bytes).")
    print("This script no longer overwrites v2_handler from app_v2.do_* blocks.")
    sys.exit(0)
