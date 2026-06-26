"""P5 Integrity-driven repair service — missing detection → plan → controlled pull."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

try:
    from protocol.constants import EXECUTION_GATE_ALLOW, EXECUTION_GATE_DENY, EXECUTION_GATE_REQUIRE_CONFIRM
    from protocol.models import ExecutionPolicy, MissingDiff, RepairPlan
except ImportError:
    from cnexus_protocol.constants import EXECUTION_GATE_ALLOW, EXECUTION_GATE_DENY, EXECUTION_GATE_REQUIRE_CONFIRM
    from cnexus_protocol.models import ExecutionPolicy, MissingDiff, RepairPlan

from .repair import (
    build_repair_plans,
    diff_all_manifests,
    diff_by_root,
    enrich_suggested_sources,
    evaluate_execution_gate,
    execute_repair_plans,
    plans_from_diff_rows,
    suggest_repair_sources,
)
from .repair.execution_policy_store import ExecutionPolicyStore
from .service import StorageService


class RepairService:
    """
    P5 facade: Chunk is repaired, not synced.
    Repair is deterministic, not autonomous — no daemon, no gossip.
    """

    def __init__(self, storage: StorageService, catalog_service=None, policy_store: Optional[ExecutionPolicyStore] = None):
        self.storage = storage
        self.catalog = catalog_service
        self.policy_store = policy_store or ExecutionPolicyStore()

    def get_execution_policy(self) -> Dict[str, Any]:
        policy = self.policy_store.get()
        return {"ok": True, "policy": policy.to_dict()}, 200

    def set_execution_policy(self, policy_row: Dict[str, Any]) -> Dict[str, Any]:
        policy = ExecutionPolicy.from_dict(policy_row or {})
        saved = self.policy_store.set(policy)
        return {"ok": True, "policy": saved.to_dict()}, 200

    def evaluate_gate(
        self,
        *,
        plans: Optional[Sequence[Dict[str, Any]]] = None,
        suggested_sources: Optional[Sequence[Dict[str, Any]]] = None,
        user_confirmed: bool = False,
        policy_row: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Preview execution gate without pulling chunks."""
        parsed = [RepairPlan.from_dict(row) for row in (plans or []) if isinstance(row, dict)]
        policy = ExecutionPolicy.from_dict(policy_row) if policy_row else self.policy_store.get()
        gate = evaluate_execution_gate(
            parsed,
            policy,
            suggested_sources=suggested_sources,
            user_confirmed=user_confirmed,
        )
        return {"ok": True, **gate}, 200

    def detect_missing(
        self,
        *,
        root_hash: str = "",
        commit_id: str = "",
        scope: str = "manifest",
    ) -> Dict[str, Any]:
        """P5.0 — Manifest ↔ ChunkStore diff."""
        if scope == "all":
            diffs = diff_all_manifests(self.storage.manifests, self.storage.chunks)
            return {
                "ok": True,
                "scope": "all",
                "diffs": [row.to_dict() for row in diffs],
                "count": len(diffs),
                "missing_total": sum(len(d.missing) + len(d.invalid) for d in diffs),
            }, 200

        diff = diff_by_root(
            self.storage.manifests,
            self.storage.chunks,
            root_hash=root_hash,
            commit_id=commit_id,
        )
        if diff is None:
            return {"ok": False, "error": "manifest_not_found"}, 404
        return {"ok": True, "diff": diff.to_dict()}, 200

    def generate_plan(
        self,
        *,
        root_hash: str = "",
        commit_id: str = "",
        sources: Optional[Sequence[str]] = None,
        scope: str = "manifest",
    ) -> Dict[str, Any]:
        """P5.1 — Repair intent from diff (does not pull)."""
        hints = self._catalog_hints()
        if scope == "all":
            diffs = diff_all_manifests(self.storage.manifests, self.storage.chunks)
            plans = plans_from_diff_rows(diffs, sources=sources, catalog_hints=hints)
            return {
                "ok": True,
                "scope": "all",
                "plans": [p.to_dict() for p in plans],
                "count": len(plans),
            }, 200

        diff = diff_by_root(
            self.storage.manifests,
            self.storage.chunks,
            root_hash=root_hash,
            commit_id=commit_id,
        )
        if diff is None:
            return {"ok": False, "error": "manifest_not_found"}, 404
        hint = hints.get(diff.graph_id) or {}
        plans = build_repair_plans(
            diff,
            sources=sources,
            graph_importance=float(hint.get("importance") or 1.0),
            commit_recency=float(hint.get("updated_at") or 0.0),
            head_generation=int(hint.get("head_generation") or 1),
        )
        return {"ok": True, "diff": diff.to_dict(), "plans": [p.to_dict() for p in plans], "count": len(plans)}, 200

    def execute(
        self,
        *,
        plans: Optional[Sequence[Dict[str, Any]]] = None,
        root_hash: str = "",
        commit_id: str = "",
        sources: Optional[Sequence[str]] = None,
        suggested_sources: Optional[Sequence[Dict[str, Any]]] = None,
        verifier_peer_id: str = "",
        max_concurrent: int = 0,
        max_plans: int = 0,
        user_confirmed: bool = False,
        policy_row: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """P5.3 — Execution boundary: policy gate before controlled pull."""
        policy = ExecutionPolicy.from_dict(policy_row) if policy_row else self.policy_store.get()
        if max_concurrent <= 0:
            max_concurrent = int(policy.max_concurrency)
        if max_plans <= 0:
            max_plans = int(policy.max_plans)

        parsed: List[RepairPlan] = []
        if plans:
            for row in plans:
                try:
                    parsed.append(RepairPlan.from_dict(row))
                except Exception:
                    continue
        else:
            gen, status = self.generate_plan(
                root_hash=root_hash,
                commit_id=commit_id,
                sources=sources,
            )
            if status != 200:
                return gen, status
            parsed = [RepairPlan.from_dict(row) for row in gen.get("plans") or []]

        if not parsed:
            return {"ok": True, "executed": 0, "repaired": 0, "results": [], "message": "nothing_to_repair"}, 200

        if sources and any(not p.sources for p in parsed):
            parsed = [
                RepairPlan(
                    chunk_hash=p.chunk_hash,
                    priority=p.priority,
                    sources=tuple(sources) if not p.sources else p.sources,
                    strategy=p.strategy,
                    root_hash=p.root_hash,
                    graph_id=p.graph_id,
                    commit_id=p.commit_id,
                )
                for p in parsed
            ]

        gate = evaluate_execution_gate(
            parsed,
            policy,
            suggested_sources=suggested_sources,
            user_confirmed=user_confirmed,
        )

        if gate.get("gate") == EXECUTION_GATE_REQUIRE_CONFIRM:
            return {
                "ok": False,
                "error": "confirm_required",
                "gate": gate,
                "message": "Repair execution requires explicit user confirmation",
            }, 409

        if gate.get("gate") == EXECUTION_GATE_DENY:
            return {
                "ok": False,
                "error": "execution_denied",
                "gate": gate,
                "message": "Repair execution denied by policy or probe evidence",
            }, 403

        allowed = [RepairPlan.from_dict(row) for row in gate.get("allowed_plans") or []]
        if not allowed:
            return {"ok": True, "executed": 0, "repaired": 0, "results": [], "gate": gate, "message": "nothing_permitted"}, 200

        report = execute_repair_plans(
            self.storage,
            allowed,
            verifier_peer_id=verifier_peer_id,
            max_concurrent=max_concurrent,
            max_plans=max_plans,
        )
        report["gate"] = gate
        report["execution_policy"] = policy.to_dict()
        return report, 200 if report.get("repaired", 0) > 0 or report.get("executed") == 0 else 502

    def _catalog_hints(self) -> Dict[str, Dict[str, Any]]:
        if self.catalog is None:
            return {}
        hints: Dict[str, Dict[str, Any]] = {}
        for gid in self.catalog.store.graph_ids():
            entry = self.catalog.store.get_entry(gid)
            if entry is None:
                continue
            hints[gid] = {
                "importance": 1.0,
                "updated_at": float(entry.updated_at),
                "head_generation": int(entry.head_generation),
            }
        return hints

    def build_connect_hook(
        self,
        *,
        peer_host: str,
        peer_id: str = "",
        peer_registry=None,
        probe_sources: bool = True,
        include_gate: bool = True,
    ) -> Dict[str, Any]:
        """
        P5.1 + P5.2 + P5.3 connect observability hook.
        Returns missing + repair_plans + suggested_sources (+ probe + gate preview).
        Suggested only — never executes repair.
        """
        diffs = diff_all_manifests(self.storage.manifests, self.storage.chunks)
        missing: List[str] = []
        invalid: List[str] = []
        for diff in diffs:
            missing.extend(diff.missing)
            invalid.extend(diff.invalid)

        descriptor_hosts: List[str] = []
        if self.storage.descriptors is not None:
            for root in self.storage.manifests.list_roots():
                manifest = self.storage.manifests.get(root)
                if manifest is None:
                    continue
                for chunk_hash in manifest.chunk_hashes():
                    desc = self.storage.descriptors.get(chunk_hash)
                    if desc and desc.sources:
                        descriptor_hosts.extend(desc.sources)

        suggested = suggest_repair_sources(
            connected_host=peer_host,
            connected_peer_id=peer_id,
            peer_registry=peer_registry,
            descriptor_sources=descriptor_hosts,
        )
        repair_targets = missing + invalid
        if probe_sources:
            suggested = enrich_suggested_sources(suggested, repair_targets)

        source_hosts = [str(row.get("host") or "") for row in suggested if row.get("host")]

        hints = self._catalog_hints()
        plans = plans_from_diff_rows(diffs, sources=source_hosts, catalog_hints=hints)

        payload: Dict[str, Any] = {
            "ok": True,
            "suggested_only": True,
            "executed": False,
            "policy": "connect_observability_hook",
            "probe_enabled": bool(probe_sources),
            "missing": missing,
            "invalid": invalid,
            "missing_count": len(missing) + len(invalid),
            "diffs": [d.to_dict() for d in diffs],
            "repair_plans": [p.to_dict() for p in plans],
            "plan_count": len(plans),
            "suggested_sources": suggested,
            "execution_policy": self.policy_store.get().to_dict(),
            "next_steps": {
                "preview_gate": "POST /api/storage/repair/gate",
                "execute": "POST /api/storage/repair/execute (requires confirm:true)",
            },
        }
        if include_gate and plans:
            gate_payload, _ = self.evaluate_gate(
                plans=[p.to_dict() for p in plans],
                suggested_sources=suggested,
                user_confirmed=False,
            )
            payload["execution_gate"] = gate_payload
        return payload

