#!/usr/bin/env python3
"""
LAN dual-node smoke — connect → application control → optional repair execute.

Run on Node A while Node B is reachable and has published content.

Examples:
  python scripts/lan_dual_node_smoke.py --peer-id aa...aa
  python scripts/lan_dual_node_smoke.py --peer-id aa...aa --remote-host http://192.168.1.105:7864
  python scripts/lan_dual_node_smoke.py --peer-id aa...aa --confirm-repair
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def _request(
    method: str,
    url: str,
    body: dict | None = None,
    *,
    timeout: float = 20.0,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw or str(exc)}
        return exc.code, payload


def _ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"OK   {label}{suffix}")


def _fail(label: str, detail: str) -> None:
    print(f"FAIL {label} — {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CNexus LAN dual-node smoke (run on Node A)")
    parser.add_argument("--local", default="http://127.0.0.1:7864", help="Node A gateway base URL")
    parser.add_argument("--remote-host", default="", help="Optional Node B base URL for reachability probe")
    parser.add_argument("--peer-id", required=True, help="Node B Ed25519 pubkey (64 hex)")
    parser.add_argument("--confirm-repair", action="store_true", help="Execute repair after gate preview")
    parser.add_argument("--skip-connect", action="store_true", help="Skip connect (use existing session state)")
    args = parser.parse_args()

    local = str(args.local).rstrip("/")
    peer_id = str(args.peer_id).strip().lower()
    failures: list[str] = []

    print(f"CNexus LAN dual-node smoke @ {local}\n")

    # 1. Local identity
    status, ident = _request("GET", f"{local}/api/connectivity/identity")
    if status == 200 and ident.get("ok") and ident.get("pubkey"):
        _ok("local identity", str(ident.get("pubkey", ""))[:16] + "…")
    else:
        msg = str(ident.get("error") or f"HTTP {status}")
        _fail("local identity", msg)
        failures.append("local identity")

    # 2. Application status
    status, app_status = _request("GET", f"{local}/api/application/status")
    if status == 200 and app_status.get("ok"):
        control = app_status.get("control") or {}
        _ok("application status", f"phase={control.get('phase', 'idle')}")
    else:
        _fail("application status", str(app_status.get("error") or f"HTTP {status}"))
        failures.append("application status")

    # 3. Remote reachability (optional)
    remote = str(args.remote_host or "").strip().rstrip("/")
    if remote:
        status, remote_ident = _request("GET", f"{remote}/api/connectivity/identity")
        if status == 200 and remote_ident.get("ok"):
            _ok("remote identity", remote)
        else:
            _fail("remote identity", str(remote_ident.get("error") or f"HTTP {status}"))
            failures.append("remote identity")

    connect_payload: dict[str, Any] = {}
    hook: dict[str, Any] = {}
    application: dict[str, Any] = {}

    if not args.skip_connect:
        # 4. Connect
        connect_body: dict[str, Any] = {"peer_id": peer_id}
        if remote:
            connect_body["host"] = remote
        status, connect_payload = _request("POST", f"{local}/api/connectivity/connect", connect_body)
        if status == 200 and connect_payload.get("ok"):
            path = str(connect_payload.get("path_kind") or connect_payload.get("url") or "ok")
            _ok("connect", path)
        else:
            _fail("connect", str(connect_payload.get("error") or f"HTTP {status}"))
            failures.append("connect")
            print("\n--- connect response ---")
            print(json.dumps(connect_payload, indent=2, ensure_ascii=False))
            return 1

        hook = connect_payload.get("repair_hook") or {}
        application = connect_payload.get("application") or {}
        if hook.get("executed"):
            _fail("repair_hook.executed", "must be false on connect")
            failures.append("hook executed")
        else:
            _ok("repair_hook.executed", "false")

        phase = str(application.get("phase") or (application.get("control") or {}).get("phase") or "")
        missing = int(hook.get("missing_count") or 0)
        _ok("application phase", f"{phase or '—'} missing={missing}")

        gate = application.get("execution_gate") or hook.get("execution_gate") or {}
        if missing > 0:
            if gate.get("gate"):
                _ok("execution_gate preview", str(gate.get("gate")))
            else:
                _fail("execution_gate preview", "missing gate on non-zero missing_count")
                failures.append("execution_gate preview")
        else:
            _ok("integrity", "no missing chunks after connect")

    # 5. Diagnose
    status, diag = _request("POST", f"{local}/api/application/diagnose", {"scope": "all"})
    if status == 200 and diag.get("ok"):
        diff = diag.get("diff") or {}
        missing_total = diff.get("missing_total")
        if missing_total is None and isinstance(diff.get("diffs"), list):
            missing_total = sum(
                len(d.get("missing") or []) + len(d.get("invalid") or [])
                for d in diff["diffs"]
            )
        plan_count = int(diag.get("plan_count") or 0)
        _ok("diagnose", f"missing_total={missing_total} plans={plan_count}")
    else:
        _fail("diagnose", str(diag.get("error") or f"HTTP {status}"))
        failures.append("diagnose")

    # 6. Gate preview via application repair
    if hook.get("repair_plans") and int(hook.get("missing_count") or 0) > 0:
        status, gate_resp = _request(
            "POST",
            f"{local}/api/application/repair",
            {
                "action": "gate",
                "peer_id": peer_id,
                "peer_host": str(connect_payload.get("url") or remote or ""),
                "plans": hook.get("repair_plans"),
                "suggested_sources": hook.get("suggested_sources"),
                "confirm": False,
            },
        )
        if status == 200 and gate_resp.get("gate"):
            _ok("repair gate", str(gate_resp.get("gate")))
        else:
            _fail("repair gate", str(gate_resp.get("error") or f"HTTP {status}"))
            failures.append("repair gate")

        if args.confirm_repair:
            status, exec_resp = _request(
                "POST",
                f"{local}/api/application/repair",
                {
                    "action": "execute",
                    "confirm": True,
                    "peer_id": peer_id,
                    "peer_host": str(connect_payload.get("url") or remote or ""),
                    "plans": hook.get("repair_plans"),
                    "suggested_sources": hook.get("suggested_sources"),
                },
            )
            if status == 200 and int(exec_resp.get("repaired") or 0) > 0:
                _ok("repair execute", f"repaired={exec_resp.get('repaired')}")
            elif status == 403:
                _fail("repair execute", "403 denied — probe or policy")
                failures.append("repair execute")
            elif status == 409:
                _fail("repair execute", "409 confirm_required")
                failures.append("repair execute")
            else:
                _fail("repair execute", str(exec_resp.get("error") or f"HTTP {status}"))
                failures.append("repair execute")

            # Re-diagnose
            status, diag2 = _request("POST", f"{local}/api/application/diagnose", {"scope": "all"})
            if status == 200:
                diff2 = diag2.get("diff") or {}
                mt = diff2.get("missing_total")
                if mt is None:
                    mt = 0
                if int(mt or 0) == 0:
                    _ok("post-repair diagnose", "missing_total=0")
                else:
                    _fail("post-repair diagnose", f"missing_total={mt}")
                    failures.append("post-repair diagnose")
    elif args.confirm_repair:
        _fail("confirm-repair", "no repair plans — publish on Node B first")
        failures.append("confirm-repair")

    print()
    if failures:
        print(f"FAILED ({len(failures)}): {', '.join(failures)}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
